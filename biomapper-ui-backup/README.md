# Biomapper UI

A modern React-based frontend for the Biomapper biological data harmonization and ontology mapping toolkit.

## Overview

This UI provides a user-friendly interface to the Biomapper toolkit, allowing researchers to:

1. Upload CSV files containing biological identifiers
2. Select columns containing IDs for mapping
3. Configure mapping operations to target ontologies
4. Track mapping job status in real-time
5. Download enriched results with mapped identifiers

## Architecture

### Key Technologies

- **React + TypeScript**: Core UI framework with type safety
- **Vite**: Fast, modern build tool
- **Mantine**: Component library for modern UI elements
- **React Query**: Data fetching and state management
- **Axios**: HTTP client for API requests

### Integration with Biomapper

The UI interfaces with the FastAPI backend, which in turn leverages the Biomapper library's hybrid architecture:

1. **SPOKE Knowledge Graph**: Primary source of biological relationships (ArangoDB)
2. **Extension Graph**: Custom graph to fill gaps in SPOKE's coverage (ArangoDB)
3. **Unified Ontology Layer**: Coordinates between both graphs
4. **SQL-based Mapping Cache**: Optimizes performance

```js
export default tseslint.config({
  extends: [
    // Remove ...tseslint.configs.recommended and replace with this
    ...tseslint.configs.recommendedTypeChecked,
    // Alternatively, use this for stricter rules
    ...tseslint.configs.strictTypeChecked,
    // Optionally, add this for stylistic rules
    ...tseslint.configs.stylisticTypeChecked,
  ],
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config({
  plugins: {
    // Add the react-x and react-dom plugins
    'react-x': reactX,
    'react-dom': reactDom,
  },
  rules: {
    // other rules...
    // Enable its recommended typescript rules
    ...reactX.configs['recommended-typescript'].rules,
    ...reactDom.configs.recommended.rules,
  },
})
```
