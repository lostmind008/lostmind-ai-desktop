import { redirect } from 'next/navigation';

export default function HomePage() {
  // Redirect to chat page
  redirect('/chat');
}

export const metadata = {
  title: 'LostMindAI - Intelligent AI Assistant',
  description: 'Experience the power of advanced AI with LostMindAI',
};