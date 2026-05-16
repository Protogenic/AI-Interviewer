export async function transcribeAudio(
  blob: Blob,
  opts?: { language?: string; filename?: string }
): Promise<string> {
  const url = import.meta.env.VITE_STT_URL || 'http://localhost:8010';
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 20000);

  const form = new FormData();
  form.append('audio', blob, opts?.filename ?? 'audio.webm');
  if (opts?.language) form.append('language', opts.language);

  try {
    const res = await fetch(`${url}/stt`, {
      method: 'POST',
      body: form,
      signal: controller.signal,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(text || `STT error: ${res.status}`);
    }

    const data = (await res.json()) as { text?: string };
    return (data.text ?? '').trim();
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('STT сервис отвечает слишком долго. Попробуйте более короткую запись.');
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

