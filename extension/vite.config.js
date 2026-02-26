import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    plugins: [react()],
    base: '',
    build: {
        outDir: 'dist',
        emptyOutDir: true,
        rollupOptions: {
            input: {
                sidepanel: resolve(__dirname, 'sidepanel.html'),
                background: resolve(__dirname, 'src/background.js'),
            },
            output: {
                entryFileNames: '[name].js',
                chunkFileNames: '[name].js',
                assetFileNames: '[name].[ext]',
            },
        },
    },
    // Copy public/ (manifest, icons) as-is
    publicDir: 'public',
});
