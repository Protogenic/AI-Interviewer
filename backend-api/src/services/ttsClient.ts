import axios from 'axios';

const TTS_SERVICE_URL = process.env.TTS_SERVICE_URL ?? 'http://localhost:8100';

export async function synthesize(text: string, voiceId: string): Promise<string | null> {
  try {
    const response = await axios.post(
      `${TTS_SERVICE_URL}/api/synthesize`,
      { text, voice_id: voiceId },
      { responseType: 'arraybuffer', timeout: 120_000 },
    );
    return Buffer.from(response.data).toString('base64');
  } catch (err) {
    console.error('[TTS] synthesis failed', err instanceof Error ? err.message : err);
    return null;
  }
}
