'use client';

import { Suspense } from 'react';
import { useParams } from 'next/navigation';
import DealerProfile from '@/components/dealers/DealerProfile';

export default function DealerDetailsPage() {
  const { dealerId } = useParams();
  return (
    <Suspense fallback={null}>
      <DealerProfile key={dealerId} dealerId={decodeURIComponent(dealerId)} />
    </Suspense>
  );
}
