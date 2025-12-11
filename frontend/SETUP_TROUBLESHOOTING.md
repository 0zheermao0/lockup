# Frontend Setup & Troubleshooting Guide

This guide helps you resolve common frontend startup issues, especially the "pre-transform error" that some users may encounter.

## Prerequisites

### Node.js Version Requirements
**CRITICAL:** This project requires specific Node.js versions:
- **Node.js 20.19.0 or higher**
- **OR Node.js 22.12.0 or higher**

Check your version:
```bash
node --version
npm --version
```

If you have an incompatible version, please install a compatible Node.js version from [nodejs.org](https://nodejs.org/).

## Quick Setup

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Environment Configuration
**REQUIRED:** Copy the environment file:
```bash
cp .env.example .env
```

The `.env` file contains important configuration for API connections. The default development configuration should work out of the box.

### 3. Start Development Server
```bash
npm run dev
```

The frontend should start at `http://localhost:5173/`

## Common Issues & Solutions

### Issue 1: "pre-transform error" on startup

This error typically occurs due to one of the following reasons:

#### **Solution A: Node.js Version Incompatibility**
**Most Common Cause:** Using an incompatible Node.js version.

```bash
# Check your Node.js version
node --version

# If version is below 20.19.0 or between 21.x-22.11.x:
# Install Node.js 20.19.0+ or 22.12.0+ from https://nodejs.org/
```

#### **Solution B: Missing Environment File**
```bash
# Ensure .env file exists
ls -la .env

# If missing, copy from example:
cp .env.example .env
```

#### **Solution C: Clean Installation**
```bash
# Remove node_modules and reinstall
rm -rf node_modules
rm package-lock.json
npm install
```

#### **Solution D: Clear Vite Cache**
```bash
# Clear Vite cache and restart
rm -rf node_modules/.vite
npm run dev
```

### Issue 2: Module Resolution Errors

If you see errors about modules not being found:

```bash
# Ensure TypeScript is properly configured
npm run type-check

# If type checking fails, try:
rm -rf node_modules/.tmp
npm run type-check
```

### Issue 3: Port Already in Use

If port 5173 is busy, Vite will automatically try the next available port (5174, 5175, etc.). This is normal behavior.

### Issue 4: API Connection Issues

If the frontend starts but can't connect to the backend:

1. **Ensure backend is running** on `http://localhost:8000`
2. **Check .env configuration:**
   ```
   VITE_API_BASE_URL=/api
   ```
3. **Verify proxy configuration** in `vite.config.ts` is pointing to the correct backend URL

## Development Environment Verification

### Check All Systems
```bash
# 1. Verify Node.js version
node --version  # Should be 20.19.0+ or 22.12.0+

# 2. Verify environment file
cat .env  # Should contain VITE_API_BASE_URL

# 3. Run type checking
npm run type-check  # Should complete without errors

# 4. Start development server
npm run dev  # Should start successfully
```

### Expected Output
When everything is working correctly, you should see:
```
VITE v7.x.x ready in XXXms

➜  Local:   http://localhost:5173/
➜  Vue DevTools: Open http://localhost:5173/__devtools__/ as a separate window
```

## Advanced Troubleshooting

### For Persistent Issues

1. **Check system compatibility:**
   ```bash
   # Verify operating system compatibility
   uname -a  # On macOS/Linux
   ver       # On Windows
   ```

2. **Update npm and Node.js:**
   ```bash
   npm install -g npm@latest
   # Then install compatible Node.js version
   ```

3. **Reset entire environment:**
   ```bash
   rm -rf node_modules
   rm package-lock.json
   rm -rf .vite
   npm cache clean --force
   npm install
   npm run dev
   ```

### Getting Help

If you continue to experience issues:

1. **Check Node.js version** - This is the #1 cause of startup issues
2. **Verify .env file exists** and contains proper configuration
3. **Try clean installation** as described above
4. **Report the issue** with the following information:
   - Your Node.js version (`node --version`)
   - Your npm version (`npm --version`)
   - Operating system
   - Complete error message
   - Steps you've already tried

## Production Build

To build for production:
```bash
npm run build
npm run preview  # Preview production build locally
```

## Additional Commands

```bash
npm run type-check  # TypeScript type checking
npm run lint        # ESLint code linting
npm run build-only  # Build without type checking
```