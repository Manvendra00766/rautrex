import React from 'react';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  /**
   * Border radius for the skeleton element
   * @default "md"
   */
  radius?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | 'full' | string;
}

/**
 * Reusable skeleton loader component for consistent loading states
 * Prevents layout shift by matching the dimensions of actual content
 */
export default function Skeleton({
  width = '100%',
  height = '1rem',
  className = '',
  radius = 'md',
}: SkeletonProps) {
  // Convert width/height to string if they're numbers (assume pixels)
  const widthStr = typeof width === 'number' ? `${width}px` : width;
  const heightStr = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={`animate-pulse bg-slate-900/50 rounded-${radius} ${className}`}
      style={{ width: widthStr, height: heightStr }}
    />
  );
}