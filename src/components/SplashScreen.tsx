import { motion } from 'motion/react';

export function SplashScreen({ statusText }: { statusText?: string }) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#040507] px-8 text-zinc-100">
      <motion.div
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
        className="flex flex-col items-center"
      >
        <div className="glass-surface relative flex h-20 w-20 items-center justify-center rounded-[26px]">
          <svg width="36" height="36" viewBox="0 0 36 36" fill="none" aria-hidden="true">
            <path
              d="M18 3L31 10.5V25.5L18 33L5 25.5V10.5L18 3Z"
              stroke="white"
              strokeWidth="2"
              strokeLinejoin="round"
            />
            <path
              d="M18 9L25.5 13.3V22.7L18 27L10.5 22.7V13.3L18 9Z"
              fill="white"
              fillOpacity="0.92"
            />
          </svg>
        </div>

        <h1 className="mt-6 text-xl font-bold tracking-tight text-white">New NFT</h1>
        <p className="mt-1.5 text-xs font-medium tracking-wide text-zinc-500">
          {statusText || 'Синхронизация профиля...'}
        </p>

        <div className="mt-6 h-1 w-40 overflow-hidden rounded-full bg-white/10">
          <motion.div
            className="h-full w-1/2 rounded-full bg-white"
            initial={{ x: '-100%' }}
            animate={{ x: '200%' }}
            transition={{ repeat: Infinity, duration: 1.15, ease: 'easeInOut' }}
          />
        </div>
      </motion.div>
    </div>
  );
}
