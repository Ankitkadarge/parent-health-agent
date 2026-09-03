"use client";

import { useEffect, useRef } from "react";
import FamilySignupForm from "@/components/FamilySignupForm";

export default function HomePage() {
  const navWrapRef = useRef<HTMLDivElement>(null);
  const revealRefs = useRef<(HTMLElement | null)[]>([]);

  useEffect(() => {
    const el = navWrapRef.current;
    if (!el) return;
    const setNav = () => el.classList.toggle("scrolled", window.scrollY > 8);
    setNav();
    window.addEventListener("scroll", setNav, { passive: true });
    return () => window.removeEventListener("scroll", setNav);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    revealRefs.current.forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const addReveal = (el: HTMLElement | null) => {
    if (el && !revealRefs.current.includes(el)) revealRefs.current.push(el);
  };

  return (
    <>
      <header className="nav-wrap" id="navWrap" ref={navWrapRef}>
        <div className="container nav">
          <a className="brand" href="#top" aria-label="Parent Health Agent home">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 3c2.8 3.2 4.7 5.8 4.7 8.5A4.7 4.7 0 0 1 12 16.2a4.7 4.7 0 0 1-4.7-4.7C7.3 8.8 9.2 6.2 12 3Z"
                  fill="#fff"
                />
                <path
                  d="M7 18.2c1.5 1.4 3.2 2.1 5 2.1s3.5-.7 5-2.1"
                  stroke="#fff"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                />
              </svg>
            </span>
            <span>Parent Health Agent</span>
          </a>
          <nav className="nav-links" aria-label="Primary navigation">
            <a href="#how">How it works</a>
            <a href="#families">For families</a>
            <a href="#safety">Safety</a>
          </nav>
          <a href="#signup" className="nav-cta">
            Get started
          </a>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="container hero-grid">
            <div>
              <span className="eyebrow">
                <span className="dot"></span> WhatsApp family health setup for Indian families
              </span>
              <h1>
                Stay close to
                <br />
                your parent&apos;s <em className="accent">health</em>
                <br />
                over WhatsApp
              </h1>
              <p>
                A simple WhatsApp setup that gets your parent&apos;s health basics recorded in
                one place — so the family isn&apos;t starting from scratch every time it comes up.
              </p>
              <div className="hero-actions">
                <a className="btn btn-primary" href="#signup">
                  Get started
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                    <path
                      d="m9 18 6-6-6-6"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </a>
                <a className="btn btn-ghost" href="#how">
                  See how it works
                </a>
              </div>
              <div className="micro">
                <svg viewBox="0 0 24 24" fill="none">
                  <path
                    d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  />
                  <path
                    d="m8.5 12 2.2 2.2 4.8-5"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                No app to install. Just WhatsApp, in the language your parent already speaks.
              </div>
            </div>

            <div className="hero-visual" aria-label="Parent and child using WhatsApp check-ins">
              <div className="photo-card">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/parent-hero.jpg" alt="A parent smiling while looking at their phone" />
              </div>

              <div className="distance-card">
                <strong>Built for families living apart</strong>
                <span>Care shouldn&apos;t depend on living in the same city.</span>
              </div>

              <div className="wa-card">
                <div className="wa-top">
                  <div className="wa-avatar">
                    <svg viewBox="0 0 24 24" fill="none">
                      <path
                        d="M12 3c2.8 3.2 4.7 5.8 4.7 8.5A4.7 4.7 0 0 1 12 16.2a4.7 4.7 0 0 1-4.7-4.7C7.3 8.8 9.2 6.2 12 3Z"
                        fill="#fff"
                      />
                    </svg>
                  </div>
                  <div>
                    <div className="wa-name">Family Health Check-in</div>
                    <div className="wa-status">
                      <span className="live-dot"></span> Active on WhatsApp
                    </div>
                  </div>
                </div>
                <div className="wa-thread">
                  <div className="wa-bubble bot">
                    Namaste! Have you been diagnosed with diabetes by a doctor?
                  </div>
                  <div className="wa-bubble reply">Haan, pichle saal se.</div>
                  <div className="wa-bubble bot">
                    Samajh gaya. Are you currently taking any medication for it?
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="container stats reveal" ref={addReveal}>
            <div className="stats-grid">
              <div className="stat">
                <strong>WhatsApp-first</strong>
                <span>Designed around the app your parent already uses every day.</span>
              </div>
              <div className="stat">
                <strong>Family-aware</strong>
                <span>Helps caregivers stay connected without constant calling or nagging.</span>
              </div>
              <div className="stat">
                <strong>India-focused</strong>
                <span>Built for Indian families and Indian languages, from day one.</span>
              </div>
            </div>
          </div>
        </section>

        <section className="section impact">
          <div className="container">
            <span className="eyebrow">
              <span className="dot"></span> Why this matters
            </span>
            <h2 className="section-title reveal" ref={addReveal}>
              Chronic condition care in India, by the numbers.
            </h2>

            <div className="impact-layout">
              <div className="impact-numbers reveal" ref={addReveal}>
                <div className="impact-number-card">
                  <strong>101M</strong>
                  <span>Indians living with diabetes</span>
                </div>
                <div className="impact-number-card">
                  <strong>136M</strong>
                  <span>Indians who are prediabetic</span>
                </div>
              </div>

              <div className="impact-bars reveal" ref={addReveal}>
                <div className="impact-bar-row">
                  <div className="impact-bar-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <rect
                        x="3.5"
                        y="8.5"
                        width="17"
                        height="7"
                        rx="3.5"
                        transform="rotate(-45 12 12)"
                        stroke="currentColor"
                        strokeWidth="1.7"
                      />
                      <path d="M9.5 14.5l5-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                    </svg>
                  </div>
                  <div className="impact-bar-body">
                    <div className="impact-bar-label">
                      <span>Medication adherence</span>
                      <span>~50%</span>
                    </div>
                    <div className="impact-bar-track">
                      <div className="impact-bar-fill" style={{ width: "50%" }} />
                    </div>
                  </div>
                </div>

                <div className="impact-bar-row">
                  <div className="impact-bar-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path
                        d="M12 20c-4.5 0-7.5-3.5-7.5-8 0-3.2 1.8-5 3.6-5 1.2 0 1.9.7 2.4.7.5 0 1.5-.9 3-.9 1.2 0 3 .6 4 2.6"
                        stroke="currentColor"
                        strokeWidth="1.7"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <path d="M13 4c1.4 0 2.5 1.3 2.3 3-1.6.2-2.7-1-2.3-3Z" fill="currentColor" />
                    </svg>
                  </div>
                  <div className="impact-bar-body">
                    <div className="impact-bar-label">
                      <span>Diet adherence</span>
                      <span>~30%</span>
                    </div>
                    <div className="impact-bar-track">
                      <div className="impact-bar-fill" style={{ width: "30%" }} />
                    </div>
                  </div>
                </div>

                <div className="impact-bar-row">
                  <div className="impact-bar-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <circle cx="14" cy="5" r="1.6" fill="currentColor" />
                      <path
                        d="M9 20l2.4-5 2-2-1-4-3 1.5-1.5 3M11.4 9 14 8l3 2.5 3-1"
                        stroke="currentColor"
                        strokeWidth="1.7"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </div>
                  <div className="impact-bar-body">
                    <div className="impact-bar-label">
                      <span>Exercise adherence</span>
                      <span>~20%</span>
                    </div>
                    <div className="impact-bar-track">
                      <div className="impact-bar-fill" style={{ width: "20%" }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="impact-note reveal" ref={addReveal}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                <path d="M12 22s8-4.5 8-12V5l-8-3-8 3v5c0 7.5 8 12 8 12Z" stroke="currentColor" strokeWidth="1.8" />
                <path
                  d="m9 12 2 2 4-5"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>Lifestyle non-compliance is the biggest barrier in chronic disease management.</span>
            </div>

            <p className="impact-source">
              Diabetes and prediabetes figures: ICMR-INDIAB study,{" "}
              <em>The Lancet Diabetes &amp; Endocrinology</em>, 2023. Medication adherence
              figure: World Health Organization. Diet and exercise adherence are commonly
              cited estimates from chronic-disease research, not exact measurements — none
              of these numbers are specific to this product.
            </p>
          </div>
        </section>

        <section className="section" id="families">
          <div className="container split">
            <div className="sticky-copy reveal" ref={addReveal}>
              <span className="eyebrow">
                <span className="dot"></span> The real problem
              </span>
              <h2 className="section-title">
                Care gets harder when life puts kilometres in between.
              </h2>
              <p className="section-copy">
                A parent may be in Jaipur. Their daughter may be working in Bengaluru. The
                condition still needs daily attention — but neither side wants every
                conversation to become &ldquo;Did you check your sugar?&rdquo;
              </p>
            </div>
            <div className="story-stack">
              <article className="story-card reveal" ref={addReveal}>
                <div className="story-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    />
                    <path d="M12 7v5l3 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </div>
                <h3>Daily consistency is the difficult part</h3>
                <p>
                  Meals, activity, medicines, and follow-ups become dozens of tiny decisions
                  repeated every day.
                </p>
              </article>
              <article className="story-card reveal" ref={addReveal}>
                <div className="story-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-5 4v-4.5A2.5 2.5 0 0 1 4 13.5v-8Z"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
                <h3>Children want to help — without policing</h3>
                <p>
                  Caregivers often carry guilt from afar. A gentler, structured check-in helps
                  everyday support without turning into surveillance.
                </p>
              </article>
              <article className="story-card reveal" ref={addReveal}>
                <div className="story-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <path d="M8 4h8M9 2h6v4H9V2Z" stroke="currentColor" strokeWidth="1.8" />
                    <rect x="5" y="5" width="14" height="17" rx="3" stroke="currentColor" strokeWidth="1.8" />
                    <path d="M8 11h8M8 15h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </div>
                <h3>Nothing is written down in one place</h3>
                <p>
                  What happened today is usually buried in memory, missed calls or short
                  messages. WhatsApp check-ins keep it structured and in one thread.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="section how" id="how">
          <div className="container">
            <span
              className="eyebrow"
              style={{ background: "rgba(255,255,255,.07)", borderColor: "rgba(255,255,255,.14)", color: "#c9ead5" }}
            >
              <span className="dot"></span> How it works
            </span>
            <h2 className="section-title reveal" ref={addReveal}>
              A simple WhatsApp loop between your parent, us, and you.
            </h2>
            <p className="section-copy reveal" ref={addReveal}>
              It&apos;s simple on purpose. Your parent just replies on WhatsApp — no new app to
              learn.
            </p>
            <div className="steps">
              <article className="step reveal" ref={addReveal}>
                <div className="step-num">01 — SIGN UP</div>
                <h3>Fill in one quick form</h3>
                <p>
                  Add your own WhatsApp number and your parent&apos;s — plus their preferred
                  language. Takes under a minute.
                </p>
              </article>
              <article className="step reveal" ref={addReveal}>
                <div className="step-num">02 — VERIFY</div>
                <h3>One tap to confirm on WhatsApp</h3>
                <p>
                  You and your parent each confirm yourselves once on WhatsApp, so we know
                  we&apos;re really talking to the right people.
                </p>
              </article>
              <article className="step reveal" ref={addReveal}>
                <div className="step-num">03 — SET UP</div>
                <h3>Answer a few quick questions on WhatsApp</h3>
                <p>
                  A short structured conversation gets your parent&apos;s health basics
                  recorded, so the family has them in one place.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container">
            <span className="eyebrow">
              <span className="dot"></span> Designed for conversation
            </span>
            <h2 className="section-title reveal" ref={addReveal}>
              Built for parents, not tech experts
            </h2>
            <p className="section-copy reveal" ref={addReveal}>
              Everything happens inside WhatsApp — the app your parent already knows.
            </p>

            <div className="feature-grid">
              <article className="feature-large reveal" ref={addReveal}>
                <h3>Feels more like a friendly chat than a health form.</h3>
                <p>
                  A short, structured setup conversation — one small question at a time —
                  gets the basics recorded on WhatsApp itself.
                </p>
                <div className="dialogue">
                  <div className="bubble bot">Namaste Uncle. Have you been diagnosed with diabetes by a doctor?</div>
                  <div className="bubble parent">Haan, pichle saal se.</div>
                  <div className="bubble bot">
                    Samajh gaya. Are you currently taking any medication for it?
                  </div>
                  <div className="bubble parent">Haan, subah shaam.</div>
                </div>
              </article>

              <div className="feature-side">
                <article className="feature-small reveal" ref={addReveal}>
                  <h3>Made with the whole family in mind</h3>
                  <p>
                    The caregiver may live elsewhere, but they should still be able to
                    understand how things are going.
                  </p>
                  <div className="mini-row">
                    <div className="mini-icon">
                      <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
                        <path
                          d="M8 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM16.5 12a3.5 3.5 0 1 0 0-7M2 21v-3a5 5 0 0 1 5-5h2a5 5 0 0 1 5 5v3M15 14h1a5 5 0 0 1 5 5v2"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                        />
                      </svg>
                    </div>
                    <div>
                      <strong>Parent + caregiver</strong>
                      <span>One care journey, even across different cities.</span>
                    </div>
                  </div>
                  <div className="mini-row">
                    <div className="mini-icon">
                      <svg width="21" height="21" viewBox="0 0 24 24" fill="none">
                        <path d="M12 22s8-4.5 8-12V5l-8-3-8 3v5c0 7.5 8 12 8 12Z" stroke="currentColor" strokeWidth="1.8" />
                        <path
                          d="m9 12 2 2 4-5"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </div>
                    <div>
                      <strong>Support, not surveillance</strong>
                      <span>Designed to preserve dignity and autonomy.</span>
                    </div>
                  </div>
                </article>

                <article className="feature-small reveal" ref={addReveal} style={{ background: "#eef5f9" }}>
                  <h3>Set up in the language your parent prefers</h3>
                  <p>
                    You tell us your parent&apos;s preferred language during setup, so we know
                    how to reach them going forward.
                  </p>
                </article>
              </div>
            </div>
          </div>
        </section>

        <section className="section">
          <div className="container family-panel reveal" ref={addReveal}>
            <div className="family-img">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/family-care.jpg"
                alt="A daughter and her father smiling together while looking at a phone"
              />
            </div>
            <div className="family-copy">
              <span className="eyebrow" style={{ width: "max-content" }}>
                <span className="dot"></span> For sons &amp; daughters
              </span>
              <h2>Care for them, even from another city.</h2>
              <p>
                This is for the family member who cares deeply but cannot always be there
                because of work, studies, marriage, travel or simply living in another city.
              </p>
              <div className="check-list">
                <div className="check">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path
                      d="m5 12.5 4.5 4.5L19 7.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>Reduce repetitive &ldquo;Did you do this?&rdquo; conversations.</span>
                </div>
                <div className="check">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path
                      d="m5 12.5 4.5 4.5L19 7.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>Notice things worth a real conversation.</span>
                </div>
                <div className="check">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path
                      d="m5 12.5 4.5 4.5L19 7.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  <span>Let family calls feel like family calls again.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section" id="safety">
          <div className="container">
            <span className="eyebrow">
              <span className="dot"></span> Clear about its limits
            </span>
            <h2 className="section-title reveal" ref={addReveal}>
              Supporting your parents between doctor visits
            </h2>
            <p className="section-copy reveal" ref={addReveal}>
              This can support daily routines and conversations. It does not diagnose,
              prescribe medicine, or replace medical care.
            </p>
            <div className="safety-grid">
              <article className="safety-card reveal" ref={addReveal}>
                <svg viewBox="0 0 24 24" fill="none">
                  <path d="M12 22s8-4.5 8-12V5l-8-3-8 3v5c0 7.5 8 12 8 12Z" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M9 12h6M12 9v6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
                <h3>Clear medical boundaries</h3>
                <p>No diagnosis, no medication changes, no medical advice — ever.</p>
              </article>
              <article className="safety-card reveal" ref={addReveal}>
                <svg viewBox="0 0 24 24" fill="none">
                  <rect x="5" y="10" width="14" height="11" rx="2" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M8 10V7a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="1.8" />
                </svg>
                <h3>Privacy by design</h3>
                <p>
                  Health conversations are private. We&apos;ll always be clear with both the
                  parent and caregiver about what&apos;s shared, and for how long.
                </p>
              </article>
              <article className="safety-card reveal" ref={addReveal}>
                <svg viewBox="0 0 24 24" fill="none">
                  <path d="M12 3v18M3 12h18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
                </svg>
                <h3>Human help when it matters</h3>
                <p>
                  If something sounds concerning, we point families to their doctor — not
                  more automated advice.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="section" id="signup">
          <div className="container">
            <div className="cta-panel reveal" ref={addReveal}>
              <h2>Get started with your family.</h2>
              <p>
                Add your details and your parent&apos;s — we&apos;ll take it from there on
                WhatsApp.
              </p>
              <FamilySignupForm />
            </div>
          </div>
        </section>
      </main>

      <footer>
        <div className="container footer-row">
          <div>
            <strong style={{ color: "var(--ink)" }}>Parent Health Agent</strong>
            <br />
            WhatsApp-first support for families staying close to a parent&apos;s health.
          </div>
          <div className="footer-links">
            <a href="#safety">Safety</a>
            <a href="#signup">Get started</a>
          </div>
          <div>© {new Date().getFullYear()} Parent Health Agent</div>
        </div>
      </footer>
    </>
  );
}
