'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useState, ReactNode } from 'react';

export default function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [opacity, setOpacity] = useState(1);

  useEffect(() => {
    setOpacity(0);
    const t = setTimeout(() => setOpacity(1), 150);
    return () => clearTimeout(t);
  }, [pathname]);

  return (
    <div style={{ opacity, transition: 'opacity 0.15s ease' }}>{children}</div>
  );
}