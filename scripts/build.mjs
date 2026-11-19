import { cp, mkdir } from 'node:fs/promises';

const source = new URL('../site/', import.meta.url);
const output = new URL('../dist/', import.meta.url);

await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
