/** Direct Google Gemini API adapter for Nano Banana image generation. */
import { readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

const ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/interactions';

function imageMimeType(filename) {
  const extension = path.extname(filename).toLowerCase();
  const types = { '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp' };
  if (!types[extension]) throw new Error(`Unsupported Nano Banana reference image type: ${extension}`);
  return types[extension];
}

/** Send one prompt/reference image and atomically save Google's generated PNG. */
export async function generateNanoBanana({prompt, referenceImage, outPath}) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) throw new Error('Set GEMINI_API_KEY to use ART_BACKEND=nanobanana');
  const model = process.env.NANOBANANA_MODEL || 'gemini-nano-banana-2.1';
  if (!/^[A-Za-z0-9._-]+$/.test(model)) throw new Error('NANOBANANA_MODEL contains unsupported characters');

  const input = [{type:'text', text:prompt}];
  if (referenceImage) {
    input.push({type:'image', mime_type:imageMimeType(referenceImage),
      data:(await readFile(referenceImage)).toString('base64')});
  }
  const response = await fetch(ENDPOINT, {
    method:'POST',
    headers:{'content-type':'application/json', 'x-goog-api-key':apiKey},
    body:JSON.stringify({model, input, response_format:{
      type:'image', mime_type:'image/png', aspect_ratio:'1:1', image_size:'1K',
    }}),
    signal:AbortSignal.timeout(9*60*1000),
  });
  const responseText = await response.text();
  let result;
  try { result = JSON.parse(responseText); }
  catch { throw new Error(`Nano Banana returned HTTP ${response.status} with a non-JSON response`); }
  if (!response.ok) {
    const message = result.error?.message || result.message || response.statusText;
    throw new Error(`Nano Banana API HTTP ${response.status}: ${String(message).slice(0,1200)}`);
  }
  const encodedImage = result.output_image?.data;
  if (typeof encodedImage !== 'string' || !encodedImage) {
    const detail = result.output_text || result.status || 'response contained no image';
    throw new Error(`Nano Banana produced no image: ${String(detail).slice(0,500)}`);
  }
  const image = Buffer.from(encodedImage, 'base64');
  const pngSignature = Buffer.from([137,80,78,71,13,10,26,10]);
  if (image.length < 8 || !image.subarray(0,8).equals(pngSignature)) {
    throw new Error('Nano Banana response was not a PNG image');
  }
  const temporary = `${outPath}.tmp`;
  await writeFile(temporary, image, {flag:'w'});
  await rename(temporary, outPath);
  console.log(`Nano Banana generated ${path.basename(outPath)} with ${model}`);
}
