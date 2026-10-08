import { redirect } from 'next/navigation';

// proxy.js normally redirects "/" before this renders; this is the fallback.
export default function Home() {
  redirect('/dealers');
}
