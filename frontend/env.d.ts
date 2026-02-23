/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Telegram WebApp types for via-bot sharing
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        shareMessage?: (messageId: string) => void;
        ready?: () => void;
        expand?: () => void;
        close?: () => void;
        initData?: string;
        initDataUnsafe?: {
          user?: {
            id: number;
            first_name?: string;
            last_name?: string;
            username?: string;
          };
        };
      };
    };
  }
}

export {}
