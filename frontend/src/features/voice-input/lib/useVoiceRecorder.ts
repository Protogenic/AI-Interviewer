import { useCallback, useEffect, useRef, useState } from 'react';

export type VoiceRecorderState = 'idle' | 'recording' | 'done';

export interface UseVoiceRecorderResult {
  state: VoiceRecorderState;
  audioUrl: string | null;
  transcript: string;
  error: string | null;
  /** Идёт подключение микрофона до старта MediaRecorder */
  isArmingMic: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  clearRecording: () => void;
  isSupported: boolean;
}

function devLog(...args: unknown[]) {
  if (import.meta.env.DEV) console.log('[voice]', ...args);
}
function devWarn(...args: unknown[]) {
  if (import.meta.env.DEV) console.warn('[voice]', ...args);
}
function devError(...args: unknown[]) {
  if (import.meta.env.DEV) console.error('[voice]', ...args);
}

async function getUserMediaWithFallbacks(): Promise<MediaStream> {
  const quickAttempts: MediaStreamConstraints[] = [
    { audio: true },
    {
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    },
  ];

  let lastErr: unknown = null;
  for (const [idx, constraints] of quickAttempts.entries()) {
    try {
      devLog(`getUserMedia quick #${idx + 1}`, constraints);
      // eslint-disable-next-line no-await-in-loop
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      lastErr = e;
      devWarn(`getUserMedia quick #${idx + 1} failed`, e);
    }
  }

  const slowAttempts: MediaStreamConstraints[] = [];
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    const audioInputs = devices.filter((d) => d.kind === 'audioinput');
    devLog(
      'enumerateDevices() audioinput',
      audioInputs.map((d) => ({ deviceId: d.deviceId, label: d.label }))
    );

    const ids = audioInputs.map((d) => d.deviceId).filter(Boolean);
    const uniqueIds = Array.from(new Set(ids));
    const sorted = [
      ...uniqueIds.filter((id) => id !== 'default' && id !== 'communications'),
      ...uniqueIds.filter((id) => id === 'communications'),
      ...uniqueIds.filter((id) => id === 'default'),
    ];

    for (const id of sorted) {
      slowAttempts.push({ audio: { deviceId: { exact: id } } });
      slowAttempts.push({
        audio: {
          deviceId: { exact: id },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    }
  } catch (e) {
    devWarn('enumerateDevices failed', e);
  }

  for (const [idx, constraints] of slowAttempts.entries()) {
    try {
      devLog(`getUserMedia slow #${idx + 1}`, constraints);
      // eslint-disable-next-line no-await-in-loop
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      lastErr = e;
      devWarn(`getUserMedia slow #${idx + 1} failed`, e);
    }
  }
  throw lastErr;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognition) | undefined {
  return (
    (window as unknown as { SpeechRecognition?: new () => SpeechRecognition }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: new () => SpeechRecognition })
      .webkitSpeechRecognition
  );
}

export function useVoiceRecorder(lang = 'ru-RU'): UseVoiceRecorderResult {
  const [state, setState] = useState<VoiceRecorderState>('idle');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isArmingMic, setIsArmingMic] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const transcriptRef = useRef('');
  const streamRef = useRef<MediaStream | null>(null);
  const isRecordingRef = useRef(false);
  const opIdRef = useRef(0);
  const stopGenerationRef = useRef(0);
  const audioUrlRef = useRef<string | null>(null);

  const isSupported =
    // Хотя бы один из механизмов должен быть доступен:
    // - SpeechRecognition (текст)
    // - MediaRecorder+getUserMedia (аудио)
    typeof getSpeechRecognitionCtor() === 'function' ||
    (Boolean(navigator.mediaDevices?.getUserMedia) && typeof window.MediaRecorder !== 'undefined');

  const startRecording = useCallback(async () => {
    if (isRecordingRef.current) return;

    const opId = ++opIdRef.current;
    stopGenerationRef.current += 1; // сброс отложенного stop-timeout от прошлой сессии
    try {
      devLog('startRecording()');

      // Мгновенный UI-фидбек: сразу показываем состояние записи.
      // Даже если аудио-стрим не откроется, stop должен работать.
      isRecordingRef.current = true;
      setState('recording');
      setIsArmingMic(true);

      // на всякий случай закрываем "залипшие" ресурсы от прошлых попыток
      if (mediaRecorderRef.current?.state && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          // ignore
        }
      }
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;

      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = null;
      }
      setAudioUrl(null);
      setTranscript('');
      transcriptRef.current = '';
      setError(null);

      // SpeechRecognition — for transcript with punctuation
      const SpeechRecognitionCtor = getSpeechRecognitionCtor();
      if (SpeechRecognitionCtor) {
        const recognition = new SpeechRecognitionCtor();
        recognition.lang = lang;
        recognition.continuous = true;
        recognition.interimResults = false;

        recognition.onresult = (e: SpeechRecognitionEvent) => {
          for (let i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) {
              const chunk = e.results[i][0].transcript.trim();
              if (chunk) {
                transcriptRef.current = transcriptRef.current
                  ? `${transcriptRef.current} ${chunk}`
                  : chunk;
              }
            }
          }
        };

        // Chrome stops recognition after ~60s — restart if still recording
        recognition.onend = () => {
          if (isRecordingRef.current) {
            try {
              recognition.start();
            } catch {
              // ignore restart errors during brief gaps
            }
          }
        };

        recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
          devWarn('SpeechRecognition error:', e.error);
          if (e.error === 'audio-capture') {
            setError(
              'Распознавание речи недоступно: браузер не смог захватить аудио (audio-capture). Проверьте настройки микрофона в Windows и что устройство не занято.'
            );
          }
        };

        recognitionRef.current = recognition;
        try {
          if (isRecordingRef.current && opId === opIdRef.current) {
            recognition.start();
          }
        } catch (e) {
          // Если распознавание не стартовало (InvalidStateError и т.п.),
          // всё равно оставляем запись аудио работающей.
          devWarn('SpeechRecognition failed to start:', e);
          recognitionRef.current = null;
        }
      } else {
        recognitionRef.current = null;
      }

      // Пытаемся включить запись аудио (для предпросмотра).
      // Если Windows/драйвер не даёт открыть источник (NotReadableError),
      // голосовой ввод по SpeechRecognition всё равно может продолжать работать.
      try {
        if (!isRecordingRef.current || opId !== opIdRef.current) {
          setIsArmingMic(false);
          return;
        }
        const stream = await getUserMediaWithFallbacks();
        if (!isRecordingRef.current || opId !== opIdRef.current) {
          stream.getTracks().forEach((t) => t.stop());
          setIsArmingMic(false);
          return;
        }
        streamRef.current = stream;
        transcriptRef.current = '';
        chunksRef.current = [];

        const [track] = stream.getAudioTracks();
        devLog('got stream', {
          trackLabel: track?.label,
          trackEnabled: track?.enabled,
          trackMuted: track?.muted,
          trackReadyState: track?.readyState,
        });

        track?.addEventListener('ended', () => {
          devWarn('audio track ended');
        });

        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : '';

        devLog('MediaRecorder support', {
          hasMediaRecorder: typeof MediaRecorder !== 'undefined',
          mimeTypeChosen: mimeType || '(default)',
        });

        const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
        mediaRecorderRef.current = recorder;

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunksRef.current.push(e.data);
        };

        recorder.onerror = (e) => {
          devError('MediaRecorder error', e);
          // В случае ошибки рекордера не убиваем распознавание — просто отключаем предпросмотр аудио
          streamRef.current?.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
          mediaRecorderRef.current = null;
        };

        recorder.onstop = () => {
          devLog('MediaRecorder stopped', { chunks: chunksRef.current.length });
          const blob = new Blob(chunksRef.current, { type: mimeType || 'audio/webm' });
          const url = URL.createObjectURL(blob);
          audioUrlRef.current = url;
          setAudioUrl(url);
          setTranscript(transcriptRef.current.trim());
          streamRef.current?.getTracks().forEach((t) => t.stop());
          // Обязательно переводим в done здесь: при остановке через SpeechRecognition
          // stopRecorderIfAny() только вызывает recorder.stop(), без setState в другом месте.
          setState('done');
        };

        recorder.start(250);
        setIsArmingMic(false);
      } catch (e) {
        devWarn('Audio preview (getUserMedia) unavailable, continuing with SpeechRecognition only', e);
        // не выставляем error в UI здесь — иначе будет мешать, хотя распознавание может работать
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        mediaRecorderRef.current = null;
        setIsArmingMic(false);
      }
    } catch (err) {
      devError('Failed to start recording:', err);
      isRecordingRef.current = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setState('idle');
      setIsArmingMic(false);

      const anyErr = err as { name?: string; message?: string };
      if (anyErr?.name === 'NotReadableError') {
        setError(
          'Не удалось запустить микрофон (NotReadableError). Обычно это значит: микрофон занят приложением (Zoom/Telegram/Discord/другая вкладка) ИЛИ Windows блокирует доступ.\n\nПроверьте: Параметры Windows → Конфиденциальность и безопасность → Микрофон → доступ включён + разрешить приложениям доступ.\nТакже: Панель управления → Звук → Запись → ваш микрофон → Свойства → Дополнительно → снимите «Разрешить приложениям использовать устройство в монопольном режиме».'
        );
      } else if (anyErr?.name === 'NotAllowedError') {
        setError('Доступ к микрофону запрещён. Проверьте разрешения для сайта и ОС.');
      } else if (anyErr?.name === 'NotFoundError') {
        setError('Микрофон не найден. Проверьте, подключено ли устройство ввода и выбрано ли оно в системе.');
      } else {
        setError(anyErr?.message ? `Ошибка микрофона: ${anyErr.message}` : 'Ошибка микрофона');
      }
    }
  }, [lang]);

  const stopRecording = useCallback(() => {
    isRecordingRef.current = false;
    opIdRef.current += 1; // инвалидируем все асинхронные старты
    setIsArmingMic(false);

    const recognition = recognitionRef.current;
    recognitionRef.current = null;

    // Сначала рвём Web Speech — иначе onend/restart может задержать остановку.
    if (recognition) {
      recognition.onend = null;
      try {
        recognition.abort();
      } catch {
        try {
          recognition.stop();
        } catch {
          /* ignore */
        }
      }
    }

    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.stop();
      } catch {
        setTranscript(transcriptRef.current.trim());
        setState('done');
      }
    } else {
      setTranscript(transcriptRef.current.trim());
      setState('done');
    }

    const gen = ++stopGenerationRef.current;
    window.setTimeout(() => {
      if (gen !== stopGenerationRef.current) return;
      setState((s) => (s === 'recording' ? 'done' : s));
    }, 450);
  }, []);

  const clearRecording = useCallback(() => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    setAudioUrl(null);
    setTranscript('');
    transcriptRef.current = '';
    setError(null);
    setIsArmingMic(false);
    setState('idle');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isRecordingRef.current = false;
      if (recognitionRef.current) {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      if (mediaRecorderRef.current?.state !== 'inactive') {
        mediaRecorderRef.current?.stop();
      }
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  return {
    state,
    audioUrl,
    transcript,
    error,
    isArmingMic,
    startRecording,
    stopRecording,
    clearRecording,
    isSupported,
  };
}
