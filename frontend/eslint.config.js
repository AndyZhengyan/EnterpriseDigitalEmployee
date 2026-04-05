import pluginVue from 'eslint-plugin-vue'

export default [
  {
    ignores: ['dist/', 'node_modules/', 'coverage/'],
  },
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['src/**/*.{js,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        Promise: 'readonly',
        fetch: 'readonly',
        process: 'readonly',
      },
    },
    rules: {
      // Project uses Vite defaults (no semicolons)
      'semi': ['error', 'never'],
      // Limit line length but keep reasonable for readability
      'max-len': ['warn', { code: 120, ignoreStrings: true, ignoreComments: true }],
      // Warn on unused vars rather than error (development phase)
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    },
  },
]
