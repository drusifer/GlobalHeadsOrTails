#!/usr/bin/env node
/** Collectables adapter for the adjacent recard RTG image pipeline. */
import { readFile, writeFile, mkdir, open, unlink, rename } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const server = path.join(root, 'ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server');
const source = path.resolve(process.env.RECARD_IMAGEGEN_DIR || '../recard/tools/imagegen');
const packId = process.env.STICKER_PACK || 'twelve-clans';
if (!['twelve-clans', 'rangers-history'].includes(packId)) throw new Error('Unknown STICKER_PACK');
const rangers = packId === 'rangers-history';
const catalogPath = path.join(server, rangers ? 'sticker_catalog_rangers.json' : 'sticker_catalog.json');
const work = path.join(root, 'build', rangers ? 'rangers-art' : 'sticker-art');
const raw = path.join(work, 'raw');
const manifestPath = path.join(work, 'manifest.json');
const output = path.join(server, 'static/stickers', rangers ? packId : '');
const readCatalog = async () => JSON.parse(await readFile(catalogPath, 'utf8'));
const artworkItems = data => rangers
  ? data.families.map(f => ({id:f.id, prompt:f.forms[0].art_prompt, family:f, form:f.forms[0]}))
  : data.families.flatMap(f => f.forms.map(form => ({id:`${f.id}-${form.level}`,prompt:form.art_prompt,family:f,form})));
const selectedItems = items => {
  if (!process.env.ART_IDS) return items;
  const ids = new Set(process.env.ART_IDS.split(','));
  const known = new Set(items.map(item => item.id));
  for (const id of ids) if (!known.has(id)) throw new Error(`Unknown artwork ID ${id}`);
  return items.filter(item => ids.has(item.id));
};
const load = name => import(pathToFileURL(path.join(source, `${name}.mjs`)));
const style = 'Original whimsical tabletop RPG collectible sticker illustration, bold ink outline, rich painted colors, single centered full-body champion, square composition, clean warm ivory background, generous margin, no words, letters, numbers, labels or watermark. Maintain the clan palette and emblem. Legible at mobile card size.';

async function catalog() {
  if (rangers) throw new Error('Use make rangers-catalog for the sourced Rangers catalog');
  const text = await readFile('agents/smith.docs/collectables_catalog.md', 'utf8');
  const narrative = text.split('## Shared narrative\n\n')[1].split('\n\n##')[0];
  const families = [];
  let rarity;
  let family;
  for (const line of text.split('\n')) {
    const tier = line.match(/^## (Common|Uncommon|Rare|Legendary) /);
    if (tier) rarity = tier[1].toLowerCase();
    const heading = line.match(/^### \d+\. (.+)$/);
    if (heading) {
      family = { id: heading[1].toLowerCase().replace(/[^a-z0-9]+/g, '-'), name: heading[1], rarity, look: '', forms: [] };
      families.push(family);
    } else if (family && /^<!-- family-id: ([a-z0-9-]+) -->$/.test(line)) {
      family.id = line.match(/^<!-- family-id: ([a-z0-9-]+) -->$/)[1];
    } else if (family && line && !line.startsWith('-') && !line.startsWith('#') && !family.look) {
      family.look = line;
    }
    const form = line.match(/^- Level (\d) \*\*(.+?)\*\* — (.+?) “(.+)”$/);
    if (form) family.forms.push({level: Number(form[1]), name: form[2], quote: form[4], art_prompt: `${family.look} Depict ${form[2]}: ${form[3]} Evolution level ${form[1]} of 3. ${style}`});
  }
  if (families.length !== 12 || families.some(f => f.forms.length !== 3)) throw new Error('Expected 12 complete three-form clans');
  await writeFile(path.join(server, 'sticker_catalog.json'), JSON.stringify({pack_name:'The Twelve Clans', narrative, families}, null, 2) + '\n');
  console.log('Catalog: 12 families, 36 forms');
}

async function manifest() {
  const data = await readCatalog();
  const items = artworkItems(data).map(({id,prompt}) => ({id,prompt}));
  const {parseManifest} = await load('manifest');
  parseManifest(JSON.stringify(items), 'manifest.json');
  await mkdir(path.dirname(manifestPath), {recursive:true});
  await writeFile(manifestPath, JSON.stringify(items, null, 2) + '\n');
  console.log(`Manifest: ${items.length} artworks → ${manifestPath}`);
}

async function generate() {
  await manifest();
  const provider = process.env.ART_BACKEND || 'codex';
  if (!['codex', 'nanobanana', 'agy'].includes(provider)) {
    throw new Error('ART_BACKEND must be codex, nanobanana, or agy');
  }
  if (provider === 'nanobanana' && !process.env.GEMINI_API_KEY) {
    throw new Error('ART_BACKEND=nanobanana requires GEMINI_API_KEY in the environment');
  }
  if (provider === 'agy' && process.env.ANTIGRAVITY_YOLO === '1' && (process.env.ART_IDS || '').split(',').filter(Boolean).length !== 1) {
    throw new Error('ANTIGRAVITY_YOLO is limited to exactly one ART_IDS value; do not use it for batch generation');
  }
  const {BACKENDS, buildPrompt} = await load('backends');
  // Never use recard's legacy bypass flags. Keep normal CLI permissions.
  BACKENDS[`${provider}-safe`] = {
    writesToOutPath: true,
    isQuotaError: BACKENDS.codex.isQuotaError,
    command(id, prompt, outPath) {
      return {command:process.execPath, args:[path.join(root,'tools/sticker_art.mjs'),'backend',id,`${buildPrompt(prompt, '')} Save the generated image to ${outPath}. Use your image generation tool, never procedural artwork.`,source,root]};
    },
  };
  const {parseManifest} = await load('manifest');
  const {generateAll} = await load('run');
  const items = parseManifest(await readFile(manifestPath,'utf8'),manifestPath);
  const selected = selectedItems(items);
  if (process.env.ART_REVERSE === '1') selected.reverse();
  if (!selected.length) throw new Error('No selected image IDs');
  const parallel = Number(process.env.ART_PARALLEL || 2);
  if (!Number.isInteger(parallel) || parallel < 1 || parallel > 8) throw new Error('ART_PARALLEL must be an integer from 1 to 8');
  console.log(`Image backend: ${provider}${provider === 'nanobanana' ? ` (${process.env.NANOBANANA_MODEL || 'gemini-nano-banana-2.1'})` : provider === 'agy' ? ` (${process.env.ANTIGRAVITY_MODEL || 'account default'})` : ''}`);
  const result = await generateAll(selected,{backend:`${provider}-safe`,outDir:raw,parallel,retries:1,minSize:512,onResult:(status,item,done)=>console.log(`${status} ${done}/${selected.length} ${item.id}`)});
  console.log(result);
  if (result.fail || result.quota) process.exitCode=1;
}

async function pack() {
  const {packAll} = await load('pack');
  const result = await packAll({inDir:raw,outDir:output,size:512,quality:88,format:'webp'});
  console.log(result);
  if (result.packed !== result.total) process.exitCode=1;
}

async function verify() {
  const {imageIsValid} = await load('validate');
  const data = await readCatalog();
  const items = selectedItems(artworkItems(data));
  if (!items.length) throw new Error('No selected image IDs');
  let missing=0;
  const imageHashes = new Map();
  for(const item of items) {
    const filename=path.join(output,`${item.id}.webp`);
    if(!await imageIsValid(filename,512)) {console.error(`Missing/invalid ${filename}`);missing++;}
    else if (rangers) {
      const digest = createHash('sha256').update(await readFile(filename)).digest('hex');
      if (imageHashes.has(digest)) throw new Error(`Duplicate player bitmap: ${item.id} and ${imageHashes.get(digest)}`);
      imageHashes.set(digest,item.id);
    }
    if (rangers && item.family.forms.some(form => form.image !== `/static/stickers/${packId}/${item.id}.webp`)) {
      throw new Error(`Broken form reference ${item.id}`);
    }
  }
  console.log(`${items.length-missing}/${items.length} validated ${packId} portraits${process.env.ART_IDS ? ' (selected sample only)' : ''}`);
  if(missing) process.exitCode=1;
}
async function activate() {
  if (process.env.ART_IDS) throw new Error('Activation requires full-pack verification; remove ART_IDS');
  const data = await readCatalog();
  if (rangers && (data.families.length !== 1162 ||
      new Set(data.families.map(f=>f.id)).size !== 1162 ||
      data.families.some(f=>f.id !== `nyr-${f.player?.player_id}` ||
        f.forms.map(form=>form.level).sort().join(',') !== '1,2,3'))) {
    throw new Error('Full Rangers roster and all 3486 forms required before activation');
  }
  await verify();
  if (process.exitCode) throw new Error('Pack remains inactive: artwork incomplete');
  const registryPath = path.join(server,'sticker_packs.json');
  const registry = JSON.parse(await readFile(registryPath,'utf8'));
  if (!registry.packs.some(pack=>pack.id === packId)) throw new Error('Pack missing from registry');
  registry.active_pack_id = packId;
  await writeFile(registryPath+'.tmp',JSON.stringify(registry,null,2)+'\n');
  await rename(registryPath+'.tmp',registryPath);
  console.log(`Activated ${packId}; restart the app to refresh its immutable catalog cache`);
}
async function review() {
  // Contact sheets inspect actual artwork; never synthesize production assets.
  const items = selectedItems(artworkItems(await readCatalog()));
  if (!items.length) throw new Error('No selected image IDs');
  await mkdir(work,{recursive:true});
  const indexPath = path.join(work,'review-index.json');
  await writeFile(indexPath,JSON.stringify(items.map(i => ({id:i.id,name:i.family.name,rarity:i.family.rarity}))));
  const script = `
import json, pathlib, sys
from PIL import Image, ImageDraw
source, destination, index = map(pathlib.Path, sys.argv[1:])
items = json.loads(index.read_text())
for start in range(0, len(items), 36):
    page = items[start:start+36]
    rows = (len(page)+5)//6
    sheet = Image.new('RGB', (1200, rows*240), '#eee9dd')
    draw = ImageDraw.Draw(sheet)
    for offset, item in enumerate(page):
        x, y = (offset % 6)*200, (offset // 6)*240
        file = source / (item['id'] + '.webp')
        if file.exists():
            image = Image.open(file).convert('RGB')
            image.thumbnail((190, 210))
            sheet.paste(image, (x+(200-image.width)//2,y))
        else:
            draw.text((x+5,y+70),'MISSING ART',fill='#a00000')
        draw.text((x+5,y+213),item['name'][:27],fill='#161616')
        draw.text((x+5,y+226),item['rarity']+' / '+item['id'],fill='#161616')
    file = destination / ('review.jpg' if len(items)<=36 else 'review-%03d.jpg' % (start//36+1))
    sheet.save(file,quality=92)
    print(file)
`;
  const child = spawn('python3',['-c',script,output,work,indexPath],{stdio:'inherit'});
  process.exitCode = await new Promise(resolve=>{child.on('error',()=>resolve(1));child.on('close',resolve);});
}
async function unlock() {
  const ids=(process.env.ART_IDS || '').split(',').filter(Boolean);
  if(!ids.length || ids.some(id=>!(rangers ? /^nyr-[0-9]+$/ : /^[a-z0-9-]+-[123]$/).test(id))) throw new Error('Explicit safe ART_IDS required to clear stale locks');
  const processes=spawnSync('pgrep',['-af','sticker_art.mjs backend'],{encoding:'utf8'});
  if(processes.error || ![0,1].includes(processes.status)) throw new Error('Cannot verify active backend processes');
  for(const id of ids) {
    if(processes.stdout.includes(`backend ${id} `)) throw new Error(`Refusing to unlock active artwork ${id}`);
    await unlink(path.join(raw,`${id}.lock`));
    console.log(`Cleared confirmed stale lock: ${id}`);
  }
}
async function regenerate() {
  if (!process.env.ART_IDS) throw new Error('Explicit ART_IDS required to regenerate reviewed artwork');
  const items = selectedItems(artworkItems(await readCatalog()));
  const rejected = path.join(work, 'rejected', new Date().toISOString().replaceAll(':','-'));
  await mkdir(rejected,{recursive:true});
  for (const item of items) {
    try {await readFile(path.join(raw,`${item.id}.lock`)); throw new Error(`Artwork still active: ${item.id}`);}
    catch(error) {if (error.code !== 'ENOENT') throw error;}
    for (const [directory,extension] of [[raw,'png'],[output,'webp']]) {
      try {await rename(path.join(directory,`${item.id}.${extension}`),path.join(rejected,`${item.id}.${extension}`));}
      catch(error) {if (error.code !== 'ENOENT') throw error;}
    }
  }
  await generate();
}
async function backend() {
  const [, , , id, prompt] = process.argv;
  const validatorDirectory=process.argv[5] || path.resolve(process.cwd(),'../../../../recard/tools/imagegen');
  const projectRoot=process.argv[6] || process.cwd();
  const {imageIsValid}=await import(pathToFileURL(path.join(validatorDirectory,'validate.mjs')));
  const imagePath=path.join(process.cwd(),`${id}.png`);
  const lockPath=path.join(process.cwd(),`${id}.lock`);
  let lock;
  const deadline=Date.now()+10*60*1000;
  while(!lock) {
    try {lock=await open(lockPath,'wx');}
    catch(error) {
      if(error.code!=='EEXIST') throw error;
      if(await imageIsValid(imagePath,512)) return;
      if(Date.now()>deadline) throw new Error(`Timed out waiting for active artwork ${id}; inspect its log and lock`);
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
  }
  try {
    // Another runner may have finished between the runner's check and ours.
    if(await imageIsValid(imagePath,512)) return;
  let actualPrompt = prompt;
  let referenceImage;
  const useNanoBanana = process.env.ART_BACKEND === 'nanobanana';
  const useAgy = process.env.ART_BACKEND === 'agy';
  try {
    const reference = JSON.parse(await readFile(path.resolve(process.cwd(),'../references',`${id}.json`),'utf8'));
    if(reference.status === 'downloaded_for_visual_verification') {
      const image = path.resolve(process.cwd(),'../references',`${id}.png`);
      referenceImage = image;
      actualPrompt += useNanoBanana
        ? ` Use the attached player portrait as a likeness reference for facial identity, hairline and facial hair. ${reference.reference_scope}. Source: ${reference.source_url || reference.image_url}. The source photograph is reference only; create a fresh cartoon with the requested Rangers-era gear. Do not copy lettering or watermarks.`
        : ` A locally cached identity portrait is available at ${image}. ${useAgy ? 'Use that local image as a visual reference for the generated image.' : 'Inspect it using view_image and use it as an image-generation reference.'} Match facial identity, hairline and facial hair. ${reference.reference_scope}. Source: ${reference.source_url || reference.image_url}. The source photograph is reference only; create a fresh cartoon with the requested Rangers-era gear. Do not copy lettering or watermarks.`;
    } else {
      actualPrompt += ' The official portrait audit found no usable identity photograph. This card is disclosed as an archival cartoon interpretation with unverified facial likeness. Seek a trustworthy archive reference if available, otherwise keep the depiction an affectionate era-based artistic interpretation; do not claim a verified likeness or invent biographical facts.';
    }
  } catch(error) {if(error.code !== 'ENOENT') throw error;}
  if (process.env.ART_BACKEND === 'nanobanana') {
    const {generateNanoBanana} = await import('./nanobanana_backend.mjs');
    await generateNanoBanana({prompt:actualPrompt,referenceImage,outPath:imagePath});
    return;
  }
  const log = createWriteStream(path.join(process.cwd(),`${id}.log`));
  const agy = process.env.ART_BACKEND === 'agy';
  const destination = path.resolve(imagePath);
  const promptText = agy
    ? `${actualPrompt} Call the built-in generate_image tool and save its PNG output exactly to ${destination}. Do not create SVG or code-drawn art. If image generation is unavailable, return an error and do not substitute another method.`
    : actualPrompt;
  const args = agy
    ? ['-p', promptText, '--output-format', 'json', '--print-timeout', '10m', '--sandbox', ...(process.env.ANTIGRAVITY_YOLO === '1' ? ['--dangerously-skip-permissions'] : []), ...(process.env.ANTIGRAVITY_MODEL ? ['--model', process.env.ANTIGRAVITY_MODEL] : [])]
    : ['exec','--sandbox','workspace-write','--skip-git-repo-check',promptText];
  const child = spawn(agy ? (process.env.ANTIGRAVITY_CLI || 'agy') : 'codex',args,{cwd:agy ? projectRoot : undefined, stdio:['ignore','pipe','pipe'], timeout:10*60*1000});
  for (const stream of [child.stdout,child.stderr]) stream.on('data',data=>{log.write(data);process.stdout.write(data);});
  const code = await new Promise(resolve=>{child.on('error',error=>{console.error(error.message);resolve(1);});child.on('close',resolve);});
  log.end();
  process.exitCode=code || 0;
  } finally {await lock.close();await unlink(lockPath);}
}
const commands={catalog,manifest,generate,pack,verify,review,unlock,regenerate,activate,backend};
try {if(!commands[process.argv[2]]) throw new Error('Use catalog|manifest|generate|pack|verify|review|unlock'); await commands[process.argv[2]]();}
catch(error) {console.error(error.message);process.exitCode=1;}
