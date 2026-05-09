export async function transcribeAudio(
  blob: Blob,
  opts?: { language?: string; filename?: string }
): Promise<string> {
  const url = import.meta.env.VITE_STT_URL || 'http://localhost:8010';

  const form = new FormData();
  form.append('audio', blob, opts?.filename ?? 'audio.webm');
  if (opts?.language) form.append('language', opts.language);

  const res = await fetch(`${url}/stt`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `STT error: ${res.status}`);
  }

  const data = (await res.json()) as { text?: string };
  return (data.text ?? '').trim();
}

