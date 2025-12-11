# Lockup Community Frontend

Vue 3 + TypeScript + Vite frontend application for the Lockup Community platform.

## 🚀 Quick Start

### Prerequisites

**IMPORTANT:** This project requires specific Node.js versions:
- **Node.js 20.19.0 or higher**
- **OR Node.js 22.12.0 or higher**

Check your version:
```bash
node --version
```

### Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Setup environment (REQUIRED):**
   ```bash
   cp .env.example .env
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:5173/`

## 🔧 Troubleshooting

**Having startup issues?** See [SETUP_TROUBLESHOOTING.md](./SETUP_TROUBLESHOOTING.md) for detailed solutions to common problems including:
- "pre-transform error" fixes
- Node.js version compatibility issues
- Environment configuration problems

## 📋 Available Scripts

```bash
npm run dev         # Start development server
npm run build       # Build for production
npm run preview     # Preview production build
npm run type-check  # TypeScript type checking
npm run lint        # ESLint code linting
```

## 🛠 Development Environment

### Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

### Recommended Browser Setup

- **Chromium-based browsers** (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- **Firefox:**
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## 📁 Project Structure

```
src/
├── components/     # Reusable Vue components
├── views/         # Page-level components
├── stores/        # Pinia state management
├── router/        # Vue Router configuration
├── config/        # Application configuration
├── utils/         # Utility functions
└── assets/        # Static assets
```

## 🔗 Backend Integration

This frontend connects to the Django backend API. Ensure the backend is running on `http://localhost:8000` for development.

## 🏗 Technology Stack

- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Pinia** - State management
- **Vue Router** - Client-side routing
- **Naive UI** - Vue 3 component library
- **Axios** - HTTP client

## 📖 Type Support for `.vue` Imports

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## ⚙️ Configuration

See [Vite Configuration Reference](https://vite.dev/config/) for customization options.
