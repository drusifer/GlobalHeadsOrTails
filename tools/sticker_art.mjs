#!/usr/bin/env node
/** Collectables adapter for the adjacent recard RTG image pipeline. */
import { readFile, writeFile, mkdir, open, unlink } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const root = process.cwd();
const server = path.join(root, 'ntag424_sdm_provisioner/src/ntag424_sdm_provisioner/server');
const source = path.resolve(process.env.RECARD_IMAGEGEN_DIR || '../recard/tools/imagegen');
const raw = path.join(root, 'build/sticker-art/raw');
const manifestPath = path.join(root, 'build/sticker-art/manifest.json');
const load = name => import(pathToFileURL(path.join(source, `${name}.mjs`)));
const style = 'Original whimsical tabletop RPG collectible sticker illustration, bold ink outline, rich painted colors, single centered full-body champion, square composition, clean warm ivory background, generous margin, no words, letters, numbers, labels or watermark. Maintain the clan palette and emblem. Legible at mobile card size.';

async function catalog() {
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
  const data = JSON.parse(await readFile(path.join(server, 'sticker_catalog.json'), 'utf8'));
  const items = data.families.flatMap(f => f.forms.map(form => ({id:`${f.id}-${form.level}`,prompt:form.art_prompt})));
  const {parseManifest} = await load('manifest');
  parseManifest(JSON.stringify(items), 'manifest.json');
  await mkdir(path.dirname(manifestPath), {recursive:true});
  await writeFile(manifestPath, JSON.stringify(items, null, 2) + '\n');
  console.log(`Manifest: ${items.length} artworks → ${manifestPath}`);
}

async function generate() {
  await manifest();
  const {BACKENDS, buildPrompt} = await load('backends');
  // Never use recard's legacy bypass flags. Keep normal CLI permissions.
  BACKENDS['codex-safe'] = {
    writesToOutPath: true,
    isQuotaError: BACKENDS.codex.isQuotaError,
    command(id, prompt, outPath) {
      return {command:process.execPath, args:[path.join(root,'tools/sticker_art.mjs'),'backend',id,`${buildPrompt(prompt, '')} Save the generated image to ${outPath}. Use your image generation tool, never procedural artwork.`,source]};
    },
  };
  const {parseManifest} = await load('manifest');
  const {generateAll} = await load('run');
  const items = parseManifest(await readFile(manifestPath,'utf8'),manifestPath);
  const selected = process.env.ART_IDS ? items.filter(i => process.env.ART_IDS.split(',').includes(i.id)) : items;
  if (process.env.ART_REVERSE === '1') selected.reverse();
  if (!selected.length) throw new Error('No selected image IDs');
  const result = await generateAll(selected,{backend:'codex-safe',outDir:raw,parallel:2,retries:1,minSize:512,onResult:(status,item,done)=>console.log(`${status} ${done}/${selected.length} ${item.id}`)});
  console.log(result);
  if (result.fail || result.quota) process.exitCode=1;
}

async function pack() {
  const {packAll} = await load('pack');
  const result = await packAll({inDir:raw,outDir:path.join(server,'static/stickers'),size:512,quality:88,format:'webp'});
  console.log(result);
  if (result.packed !== result.total) process.exitCode=1;
}

async function verify() {
  const {imageIsValid} = await load('validate');
  const data = JSON.parse(await readFile(path.join(server,'sticker_catalog.json'),'utf8'));
  let missing=0;
  for(const f of data.families) for(const form of f.forms) {
    const filename=path.join(server,'static/stickers',`${f.id}-${form.level}.webp`);
    if(!await imageIsValid(filename,512)) {console.error(`Missing/invalid ${filename}`);missing++;}
  }
  console.log(`${36-missing}/36 validated sticker images`);
  if(missing) process.exitCode=1;
}
async function review() {
  // Review contact sheet only; never creates or modifies production art.
  const script = `
import json, pathlib, sys
from PIL import Image, ImageDraw
server, destination = map(pathlib.Path, sys.argv[1:])
catalog = json.loads((server / 'sticker_catalog.json').read_text())
sheet = Image.new('RGB', (1200, 1440), '#eee9dd')
draw = ImageDraw.Draw(sheet)
for index, (family, form) in enumerate((f, form) for f in catalog['families'] for form in f['forms']):
    x, y = (index % 6) * 200, (index // 6) * 240
    name = family['id'] + '-' + str(form['level'])
    file = server / 'static/stickers' / (name + '.webp')
    if file.exists():
        image = Image.open(file).convert('RGB')
        image.thumbnail((190, 210))
        sheet.paste(image, (x + (200 - image.width)//2, y))
    draw.text((x + 5, y + 213), form['name'][:29], fill='#161616')
    draw.text((x + 5, y + 226), family['rarity'] + ' / L' + str(form['level']), fill='#161616')
sheet.save(destination, quality=92)
`;
  const child = spawn('python3',['-c',script,server,path.join(root,'build/sticker-art/review.jpg')],{stdio:'inherit'});
  process.exitCode = await new Promise(resolve=>{child.on('error',()=>resolve(1));child.on('close',resolve);});
}
async function unlock() {
  const ids=(process.env.ART_IDS || '').split(',').filter(Boolean);
  if(!ids.length || ids.some(id=>!/^[a-z0-9-]+-[123]$/.test(id))) throw new Error('Explicit safe ART_IDS required to clear stale locks');
  const processes=spawnSync('pgrep',['-af','sticker_art.mjs backend'],{encoding:'utf8'});
  if(processes.error || ![0,1].includes(processes.status)) throw new Error('Cannot verify active backend processes');
  for(const id of ids) {
    if(processes.stdout.includes(`backend ${id} `)) throw new Error(`Refusing to unlock active artwork ${id}`);
    await unlink(path.join(raw,`${id}.lock`));
    console.log(`Cleared confirmed stale lock: ${id}`);
  }
}
async function backend() {
  const [, , , id, prompt] = process.argv;
  const validatorDirectory=process.argv[5] || path.resolve(process.cwd(),'../../../../recard/tools/imagegen');
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
  const log = createWriteStream(path.join(process.cwd(),`${id}.log`));
  const child = spawn('codex',['exec','--sandbox','workspace-write','--skip-git-repo-check',prompt],{stdio:['ignore','pipe','pipe'], timeout:10*60*1000});
  for (const stream of [child.stdout,child.stderr]) stream.on('data',data=>{log.write(data);process.stdout.write(data);});
  const code = await new Promise(resolve=>{child.on('error',error=>{console.error(error.message);resolve(1);});child.on('close',resolve);});
  log.end();
  process.exitCode=code || 0;
  } finally {await lock.close();await unlink(lockPath);}
}
const commands={catalog,manifest,generate,pack,verify,review,unlock,backend};
try {if(!commands[process.argv[2]]) throw new Error('Use catalog|manifest|generate|pack|verify|review|unlock'); await commands[process.argv[2]]();}
catch(error) {console.error(error.message);process.exitCode=1;}
