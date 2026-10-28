#!/usr/bin/env node
// Zero-dependency installer for this single-skill repository.

import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync, symlinkSync, cpSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PKG = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf8'));
const SKILL_FILE = join(ROOT, 'SKILL.md');

const COLORS = {
  dim: (s) => `\u001b[2m${s}\u001b[0m`,
  bold: (s) => `\u001b[1m${s}\u001b[0m`,
  green: (s) => `\u001b[32m${s}\u001b[0m`,
  yellow: (s) => `\u001b[33m${s}\u001b[0m`,
  red: (s) => `\u001b[31m${s}\u001b[0m`,
};
const useColor = process.stdout.isTTY && !process.env.NO_COLOR;
const paint = (fn, s) => (useColor ? fn(s) : s);
const dim = (s) => paint(COLORS.dim, s);
const bold = (s) => paint(COLORS.bold, s);
const green = (s) => paint(COLORS.green, s);
const yellow = (s) => paint(COLORS.yellow, s);

function fail(message, code = 1) {
  console.error(paint(COLORS.red, `error: ${message}`));
  process.exit(code);
}

function readSkill() {
  if (!existsSync(SKILL_FILE)) fail(`no SKILL.md at ${ROOT}`);
  const text = readFileSync(SKILL_FILE, 'utf8');
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/.exec(text);
  if (!match) fail('SKILL.md has no YAML frontmatter');
  const front = match[1];
  const name = /^name:\s*(.+)$/m.exec(front)?.[1]?.trim().replace(/^['"]|['"]$/g, '');
  let description = /^description:\s*(?:\|[-+]?)?\s*(.*)$/m.exec(front)?.[1]?.trim() ?? '';
  if (!description) {
    const block = /^description:\s*[|>][-+]?\s*\n((?:[ \t]+.*\n?)*)/m.exec(front)?.[1] ?? '';
    description = block.split('\n').map((line) => line.trim()).filter(Boolean).join(' ');
  }
  if (!name) fail('SKILL.md frontmatter has no name');
  return { name, description };
}

function dirSize(dir) {
  let total = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === '.git' || entry.name === 'node_modules') continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) total += dirSize(path);
    else if (entry.isFile()) total += statSync(path).size;
  }
  return total;
}

const TARGETS = {
  agents: {
    global: () => join(homedir(), '.agents', 'skills'),
    project: (root) => join(root, '.agents', 'skills'),
  },
  codex: {
    global: () => join(process.env.CODEX_HOME || join(homedir(), '.codex'), 'skills'),
    project: (root) => join(root, '.agents', 'skills'),
  },
  claude: {
    global: () => join(homedir(), '.claude', 'skills'),
    project: (root) => join(root, '.claude', 'skills'),
  },
  opencode: {
    global: () => join(homedir(), '.config', 'opencode', 'skills'),
    project: (root) => join(root, '.opencode', 'skills'),
  },
  cursor: {
    global: () => join(homedir(), '.cursor', 'skills'),
    project: (root) => join(root, '.cursor', 'skills'),
  },
};

function resolveTargetDir(name, project) {
  const target = TARGETS[name];
  if (!target) fail(`unknown target "${name}" (available: ${Object.keys(TARGETS).join(', ')})`);
  return project ? target.project(project) : target.global();
}

// Packaging files stay in the repository; only skill content is installed.
const PACKAGING = /[\\/](\.git|\.github|node_modules|\.pytest_cache|__pycache__|bin|package\.json|package-lock\.json)$/;

function isSkillContent(src) {
  return !PACKAGING.test(src);
}

function install(skill, opts) {
  const project = opts.project ? resolve(opts.project) : null;
  const pairs = opts.targets.map((target) => ({ target, dir: resolveTargetDir(target, project) }));
  let installed = 0;
  let skipped = 0;
  for (const { target, dir } of pairs) {
    const dest = join(dir, skill.name);
    const exists = existsSync(dest);
    if (exists && !opts.force) {
      console.log(`${yellow('skip')} ${skill.name} -> ${dest} ${dim('(already present, use --force to replace)')}`);
      skipped += 1;
      continue;
    }
    if (opts.dryRun) {
      console.log(`${dim('would install')} ${skill.name} -> ${dest} ${dim(`[${target}]`)}`);
      continue;
    }
    mkdirSync(dir, { recursive: true });
    if (exists) rmSync(dest, { recursive: true, force: true });
    if (opts.link) symlinkSync(ROOT, dest, 'dir');
    else cpSync(ROOT, dest, { recursive: true, verbatimSymlinks: true, preserveTimestamps: true, filter: isSkillContent });
    console.log(`${green(opts.link ? 'linked' : 'installed')} ${skill.name} -> ${dest} ${dim(`[${target}]`)}`);
    installed += 1;
  }
  console.log('');
  console.log(`${installed} installed, ${skipped} skipped${opts.dryRun ? ' (dry run)' : ''}.`);
  if (installed) console.log(dim('Start a new session so the runtime can discover the skill.'));
}

function remove(skill, opts) {
  const project = opts.project ? resolve(opts.project) : null;
  const dirs = opts.targets.map((target) => resolveTargetDir(target, project));
  let removed = 0;
  for (const dir of dirs) {
    const dest = join(dir, skill.name);
    if (!existsSync(dest)) {
      console.log(`${dim('absent')} ${dest}`);
      continue;
    }
    if (opts.dryRun) {
      console.log(`${dim('would remove')} ${dest}`);
      continue;
    }
    rmSync(dest, { recursive: true, force: true });
    console.log(`${green('removed')} ${dest}`);
    removed += 1;
  }
  console.log('');
  console.log(`${removed} removed${opts.dryRun ? ' (dry run)' : ''}.`);
}

function statusLine(skill, opts) {
  const project = opts.project ? resolve(opts.project) : null;
  const dirs = opts.targets.map((target) => resolveTargetDir(target, project));
  const found = dirs.filter((dir) => existsSync(join(dir, skill.name)));
  return found.length ? green(`installed -> ${found[0]}`) : dim('not installed');
}

function info(skill, opts) {
  const width = 96;
  const words = skill.description.replace(/\s+/g, ' ').trim().split(' ');
  const lines = [];
  let line = '';
  for (const word of words) {
    if (line && line.length + word.length + 1 > width) {
      lines.push(line);
      line = word;
    } else {
      line = line ? `${line} ${word}` : word;
    }
  }
  if (line) lines.push(line);

  console.log(bold(skill.name));
  console.log('');
  console.log(lines.join('\n'));
  console.log('');
  console.log(`package: ${PKG.name}@${PKG.version}`);
  console.log(`source:  ${ROOT}`);
  console.log(`size:    ${(dirSize(ROOT) / 1024).toFixed(1)} KiB`);
  console.log(`status:  ${statusLine(skill, opts)}`);
}

function parseArgs(argv) {
  const opts = { targets: [], project: null, force: false, link: false, dryRun: false };
  const positionals = [];
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith('-')) {
      positionals.push(arg);
      continue;
    }
    if (arg === '-g' || arg === '--global') continue;
    if (arg === '-h' || arg === '--help') { opts.help = true; continue; }
    if (arg === '-v' || arg === '--version') { opts.version = true; continue; }
    const [key, inline] = arg.replace(/^--/, '').split('=');
    const take = () => {
      if (inline !== undefined) return inline;
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('-')) fail(`--${key} needs a value`);
      i += 1;
      return next;
    };
    if (key === 'target') opts.targets.push(take());
    else if (key === 'project') opts.project = take();
    else if (key === 'force' || key === 'upgrade') opts.force = true;
    else if (key === 'link') opts.link = true;
    else if (key === 'dry-run') opts.dryRun = true;
    else fail(`unknown option ${arg}`);
  }
  if (!opts.targets.length) opts.targets.push('agents');
  return { opts, positionals };
}

function usage(skill) {
  console.log(`${bold(skill.name)} ${PKG.version} ${dim(`- ${skill.description.replace(/\s+/g, ' ').trim().slice(0, 80)}...`)}

Usage:
  npx ${PKG.name} [options]
  npx github:${PKG.repository.url.replace(/^.*github\.com[/:]/, '').replace(/\.git$/, '')} [options]

Commands:
  install (default)   Copy the skill into a skill directory
  remove              Remove an installed copy
  info                Show description, source path and install status

Options:
  --target <name>   agents (default), codex, claude, opencode, cursor. Repeatable.
  --project <dir>   Install into a project instead of the user directory
  --force           Replace an existing skill directory at the target
  --link            Symlink instead of copying (development)
  --dry-run         Print planned changes without writing
  -h, --help        Show this help
  -v, --version     Show version

Examples:
  npx github:Kayphoon/${skill.name}
  npx github:Kayphoon/${skill.name} --target codex
  npx github:Kayphoon/${skill.name} --project ./my-repo
  npx github:Kayphoon/${skill.name} remove`);
}

function main() {
  const { opts, positionals } = parseArgs(process.argv.slice(2));
  const skill = readSkill();
  if (opts.version) {
    console.log(PKG.version);
    return;
  }
  const command = positionals[0] || 'install';
  if (opts.help || command === 'help') {
    usage(skill);
    return;
  }
  if (command === 'install' || command === 'add') install(skill, opts);
  else if (command === 'remove' || command === 'uninstall' || command === 'rm') remove(skill, opts);
  else if (command === 'info' || command === 'show') info(skill, opts);
  else fail(`unknown command "${command}" (try --help)`);
}

main();
