import FamilySignupForm from "@/components/FamilySignupForm";

export default function HomePage() {
  return (
    <main className="page">
      <section className="hero">
        <h1>Stay close to your parent&apos;s health, over WhatsApp.</h1>
        <p>
          A gentle daily check-in that talks to your parent in their own language — so you know
          how they&apos;re really doing, without having to ask every day.
        </p>
      </section>

      <FamilySignupForm />
    </main>
  );
}
