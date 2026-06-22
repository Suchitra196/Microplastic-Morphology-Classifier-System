import { useState } from "react";
import type { Page } from "../App";

interface NavbarProps {
  page: Page;
  setPage: (p: Page) => void;
}

export default function Navbar({ page, setPage }: NavbarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (target: Page) => page === target;

  const navLinks: { label: string; target: Page }[] = [
    { label: "How it works", target: "landing" },
    { label: "Dashboard", target: "dashboard" },
  ];

  return (
    <nav
      className="fixed top-0 left-0 w-full z-50 flex items-center justify-between px-4 md:px-8 h-20"
      style={{
        background: "rgba(19,19,19,0.80)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderBottom: "1px solid rgba(255,255,255,0.10)",
      }}
    >
      {/* Left: Logo + nav links */}
      <div className="flex items-center gap-8">
        {/* Logo */}
        <button
          onClick={() => setPage("landing")}
          className="font-bold text-xl tracking-tight"
          style={{
            fontFamily: "'Hanken Grotesk', sans-serif",
            color: "var(--primary)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          MicroClassify
        </button>

        {/* Desktop nav links */}
        <div className="hidden md:flex items-center gap-6">
          {navLinks.map(({ label, target }) => (
            <button
              key={target}
              onClick={() => setPage(target)}
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: "0.9375rem",
                color: isActive(target) ? "var(--primary)" : "var(--on-surface-variant)",
                borderBottom: isActive(target)
                  ? "2px solid var(--primary)"
                  : "2px solid transparent",
                paddingBottom: "4px",
                paddingLeft: "8px",
                paddingRight: "8px",
                background: "none",
                border: "none",
                cursor: "pointer",
                transition: "color 0.15s, border-color 0.15s",
                fontWeight: isActive(target) ? 700 : 400,
              }}
            >
              {label}
            </button>
          ))}

          <button
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--on-surface-variant)",
              background: "none",
              border: "none",
              cursor: "pointer",
              transition: "color 0.15s",
              padding: "4px 8px",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLButtonElement).style.color = "var(--on-surface)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLButtonElement).style.color = "var(--on-surface-variant)")
            }
          >
            About
          </button>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "0.9375rem",
              color: "var(--on-surface-variant)",
              textDecoration: "none",
              padding: "4px 8px",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.color = "var(--on-surface)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.color = "var(--on-surface-variant)")
            }
          >
            GitHub
          </a>
        </div>
      </div>

      {/* Right: CTA + mobile hamburger */}
      <div className="flex items-center gap-3">
        {/* Desktop CTA */}
        <button
          onClick={() => setPage("upload")}
          className="hidden md:flex items-center gap-2 rounded-full px-4 py-2 font-semibold text-sm transition-opacity hover:opacity-90"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            background: "var(--on-surface)",
            color: "var(--background)",
            border: "none",
            cursor: "pointer",
          }}
        >
          Start analysis
          <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
            arrow_forward
          </span>
        </button>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2"
          style={{
            color: "var(--on-surface-variant)",
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Open menu"
        >
          <span className="material-symbols-outlined">
            {mobileOpen ? "close" : "menu"}
          </span>
        </button>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <div
          className="absolute top-20 left-0 w-full flex flex-col md:hidden py-4 px-4 gap-2"
          style={{
            background: "rgba(19,19,19,0.97)",
            backdropFilter: "blur(24px)",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {navLinks.map(({ label, target }) => (
            <button
              key={target}
              onClick={() => {
                setPage(target);
                setMobileOpen(false);
              }}
              style={{
                fontFamily: "'Inter', sans-serif",
                textAlign: "left",
                color: isActive(target) ? "var(--primary)" : "var(--on-surface-variant)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: "10px 8px",
                fontWeight: isActive(target) ? 700 : 400,
                fontSize: "0.9375rem",
              }}
            >
              {label}
            </button>
          ))}
          <button
            style={{
              fontFamily: "'Inter', sans-serif",
              textAlign: "left",
              color: "var(--on-surface-variant)",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "10px 8px",
              fontSize: "0.9375rem",
            }}
          >
            About
          </button>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontFamily: "'Inter', sans-serif",
              color: "var(--on-surface-variant)",
              textDecoration: "none",
              padding: "10px 8px",
              fontSize: "0.9375rem",
            }}
          >
            GitHub
          </a>
          <button
            onClick={() => {
              setPage("upload");
              setMobileOpen(false);
            }}
            className="flex items-center gap-2 rounded-full px-4 py-2 font-semibold text-sm mt-2"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              background: "var(--on-surface)",
              color: "var(--background)",
              border: "none",
              cursor: "pointer",
              width: "fit-content",
            }}
          >
            Start analysis
            <span className="material-symbols-outlined" style={{ fontSize: "18px" }}>
              arrow_forward
            </span>
          </button>
        </div>
      )}
    </nav>
  );
}
