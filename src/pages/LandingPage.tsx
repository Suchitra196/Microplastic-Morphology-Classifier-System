import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { Page } from "../App";

interface LandingPageProps {
  setPage: (p: Page) => void;
}

// ── Shared Footer ────────────────────────────────────────────────────────────
export function Footer() {
  return (
    <footer
      className="w-full py-12 px-4 md:px-8 flex flex-col md:flex-row justify-between items-center gap-8 mt-24"
      style={{
        background: "var(--surface-container-lowest)",
        borderTop: "1px solid rgba(255,255,255,0.05)",
      }}
    >
      <div
        className="text-xl font-bold"
        style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}
      >
        MicroClassify
      </div>
      <div
        className="text-sm"
        style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--secondary)" }}
      >
        © 2024 MicroClassify. All rights reserved. Precision Environmental Analysis.
      </div>
      <div className="flex gap-6">
        {["Privacy Policy", "Terms of Service", "Contact", "Status"].map((link) => (
          <a
            key={link}
            href="#"
            className="text-sm transition-opacity opacity-80 hover:opacity-100"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "var(--outline)",
              textDecoration: "none",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.color = "var(--on-surface-variant)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLAnchorElement).style.color = "var(--outline)")
            }
          >
            {link}
          </a>
        ))}
      </div>
    </footer>
  );
}

// ── Three.js Particle Background ────────────────────────────────────────────
function ThreeBackground() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = window.innerWidth;
    const height = window.innerHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    const pointLight = new THREE.PointLight(0x2dd4bf, 2, 10);
    pointLight.position.set(2, 2, 2);
    scene.add(pointLight);

    // Particle group
    const particleCount = 150;
    const particlesGroup = new THREE.Group();
    scene.add(particlesGroup);

    const geometries = [
      new THREE.IcosahedronGeometry(0.1, 0),       // Fragment
      new THREE.CylinderGeometry(0.01, 0.01, 0.5, 8), // Fiber
      new THREE.BoxGeometry(0.2, 0.05, 0.1),       // Film
    ];

    const material = new THREE.MeshPhongMaterial({
      color: 0x2dd4bf,
      transparent: true,
      opacity: 0.6,
      shininess: 100,
      emissive: 0x0e7c66,
      emissiveIntensity: 0.5,
    });

    for (let i = 0; i < particleCount; i++) {
      const geo = geometries[Math.floor(Math.random() * geometries.length)];
      const mesh = new THREE.Mesh(geo, material);

      mesh.position.set(
        (Math.random() - 0.5) * 15,
        (Math.random() - 0.5) * 15,
        (Math.random() - 0.5) * 10,
      );
      mesh.rotation.set(
        Math.random() * Math.PI,
        Math.random() * Math.PI,
        Math.random() * Math.PI,
      );

      const scale = Math.random() * 0.5 + 0.5;
      mesh.scale.set(scale, scale, scale);

      mesh.userData.velocity = new THREE.Vector3(
        (Math.random() - 0.5) * 0.01,
        (Math.random() - 0.5) * 0.01,
        (Math.random() - 0.5) * 0.01,
      );
      mesh.userData.rotSpeed = new THREE.Vector3(
        (Math.random() - 0.5) * 0.02,
        (Math.random() - 0.5) * 0.02,
        (Math.random() - 0.5) * 0.02,
      );

      particlesGroup.add(mesh);
    }

    // Mouse parallax
    let mouseX = 0;
    let mouseY = 0;
    const onMouseMove = (e: MouseEvent) => {
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMouseMove);

    // Resize handler
    const onResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    // Animation loop
    let animFrameId: number;
    const animate = () => {
      animFrameId = requestAnimationFrame(animate);

      particlesGroup.children.forEach((child) => {
        const p = child as THREE.Mesh;
        p.position.add(p.userData.velocity as THREE.Vector3);
        p.rotation.x += (p.userData.rotSpeed as THREE.Vector3).x;
        p.rotation.y += (p.userData.rotSpeed as THREE.Vector3).y;

        if (Math.abs(p.position.x) > 8) p.position.x *= -0.9;
        if (Math.abs(p.position.y) > 8) p.position.y *= -0.9;
        if (Math.abs(p.position.z) > 5) p.position.z *= -0.9;
      });

      particlesGroup.rotation.y += (mouseX * 0.1 - particlesGroup.rotation.y) * 0.05;
      particlesGroup.rotation.x += (mouseY * 0.1 - particlesGroup.rotation.x) * 0.05;

      renderer.render(scene, camera);
    };
    animate();

    // Cleanup
    return () => {
      cancelAnimationFrame(animFrameId);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      geometries.forEach((g) => g.dispose());
      material.dispose();
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
}

// ── LandingPage ──────────────────────────────────────────────────────────────
export default function LandingPage({ setPage }: LandingPageProps) {
  const howItWorksCards = [
    {
      step: "01",
      icon: "photo_camera",
      iconColor: "var(--on-surface)",
      glowColor: "rgba(87,241,219,0.2)",
      title: "Capture Image",
      desc: "Upload high-resolution microscopy scans directly into the secure portal.",
    },
    {
      step: "02",
      icon: "memory",
      iconColor: "var(--on-surface)",
      glowColor: "rgba(154,209,203,0.2)",
      title: "Extract Features",
      desc: "Advanced algorithms isolate particles from complex background noise.",
      mt: "lg:mt-8",
    },
    {
      step: "03",
      icon: "troubleshoot",
      iconColor: "var(--primary)",
      glowColor: "rgba(87,241,219,0.4)",
      title: "Classify & Score",
      titleColor: "var(--primary)",
      desc: "Deep learning models assign morphology types with confidence scoring.",
      mt: "lg:mt-16",
    },
    {
      step: "04",
      icon: "description",
      iconColor: "var(--on-surface)",
      glowColor: "rgba(255,220,192,0.2)",
      title: "Get Report",
      desc: "Export detailed analytical datasets and interactive visualizations.",
      mt: "lg:mt-24",
    },
  ];

  return (
    <div
      className="relative overflow-x-hidden"
      style={{ background: "var(--background)", minHeight: "100vh" }}
    >
      {/* Three.js background */}
      <ThreeBackground />

      {/* Ambient glow blobs */}
      <div
        className="ambient-glow"
        style={{ top: "-20vw", left: "-10vw" }}
      />
      <div
        className="ambient-glow"
        style={{
          bottom: "-20vw",
          right: "-10vw",
          background:
            "radial-gradient(circle, rgba(20,79,75,0.20) 0%, rgba(19,19,19,0) 70%)",
        }}
      />

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <header
        className="relative flex flex-col items-center justify-center text-center px-4 md:px-8 pt-32 pb-24"
        style={{ minHeight: "820px", zIndex: 10 }}
      >
        {/* Radial fade overlay */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(circle at center, transparent 0%, rgba(19,19,19,0.9) 100%)",
            zIndex: 1,
          }}
        />

        <div
          className="max-w-4xl mx-auto space-y-8 relative"
          style={{ zIndex: 2 }}
        >
          <h1
            className="text-5xl md:text-7xl font-extrabold tracking-tighter leading-tight"
            style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}
          >
            Detect and classify microplastics with{" "}
            <span className="glow-text" style={{ color: "var(--primary)" }}>
              clinical precision
            </span>
          </h1>

          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}
          >
            Next-generation morphological analysis powered by advanced machine learning
            models. Built for environmental researchers requiring uncompromising accuracy.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-8">
            {/* Primary CTA */}
            <button
              onClick={() => setPage("upload")}
              className="w-full sm:w-auto rounded-full px-8 py-4 font-bold transition-all transform hover:-translate-y-1"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "0.75rem",
                letterSpacing: "0.05em",
                background: "var(--primary)",
                color: "var(--on-primary)",
                border: "none",
                cursor: "pointer",
                boxShadow: "0 0 20px rgba(87,241,219,0.3)",
              }}
              onMouseEnter={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.boxShadow =
                  "0 0 30px rgba(87,241,219,0.5)")
              }
              onMouseLeave={(e) =>
                ((e.currentTarget as HTMLButtonElement).style.boxShadow =
                  "0 0 20px rgba(87,241,219,0.3)")
              }
            >
              Upload a sample
            </button>

            {/* Secondary CTA */}
            <button
              onClick={() => setPage("dashboard")}
              className="glass-panel w-full sm:w-auto rounded-full px-8 py-4 font-semibold flex items-center justify-center gap-2 hover:bg-white/5 transition-all"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: "0.75rem",
                letterSpacing: "0.05em",
                color: "var(--on-surface)",
                border: "none",
                cursor: "pointer",
              }}
            >
              View live dashboard
              <span className="material-symbols-outlined" style={{ fontSize: "16px" }}>
                monitoring
              </span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Metrics ─────────────────────────────────────────────────────── */}
      <section className="py-16 px-4 md:px-8 relative" style={{ zIndex: 10 }}>
        <div className="max-w-6xl mx-auto glass-panel rounded-2xl p-8 md:p-12">
          <div
            className="grid grid-cols-1 md:grid-cols-3 gap-8"
            style={{ borderColor: "rgba(255,255,255,0.1)" }}
          >
            {/* 50k+ */}
            <div
              className="flex flex-col items-center justify-center pt-8 md:pt-0 md:border-r"
              style={{ borderColor: "rgba(255,255,255,0.1)" }}
            >
              <span
                className="text-xs tracking-widest uppercase mb-2"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}
              >
                Total Analyzed
              </span>
              <div
                className="glow-text font-bold"
                style={{
                  fontFamily: "'Hanken Grotesk', sans-serif",
                  fontSize: "clamp(2.5rem,5vw,3rem)",
                  color: "var(--primary)",
                }}
              >
                50k+
              </div>
              <span
                className="mt-2"
                style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}
              >
                Samples Processed
              </span>
            </div>

            {/* 99.2% */}
            <div
              className="flex flex-col items-center justify-center pt-8 md:pt-0 md:border-r"
              style={{ borderColor: "rgba(255,255,255,0.1)" }}
            >
              <span
                className="text-xs tracking-widest uppercase mb-2"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}
              >
                Model Precision
              </span>
              <div
                className="glow-text font-bold"
                style={{
                  fontFamily: "'Hanken Grotesk', sans-serif",
                  fontSize: "clamp(2.5rem,5vw,3rem)",
                  color: "var(--secondary)",
                }}
              >
                99.2%
              </div>
              <span
                className="mt-2"
                style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}
              >
                Classification Accuracy
              </span>
              <span
                className="text-xs mt-1 text-center"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  color: "var(--outline)",
                }}
              >
                (synthetic validation — real metrics pending)
              </span>
            </div>

            {/* 4 morphology classes */}
            <div className="flex flex-col items-center justify-center pt-8 md:pt-0">
              <span
                className="text-xs tracking-widest uppercase mb-2"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}
              >
                Detection Scope
              </span>
              <div
                className="glow-text font-bold"
                style={{
                  fontFamily: "'Hanken Grotesk', sans-serif",
                  fontSize: "clamp(2.5rem,5vw,3rem)",
                  color: "var(--tertiary-fixed)",
                }}
              >
                4
              </div>
              <span
                className="mt-2"
                style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}
              >
                Morphology Classes
              </span>
              <span
                className="text-xs mt-1"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: "var(--outline)" }}
              >
                Fiber / Film / Fragment / Pellet
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section className="py-24 px-4 md:px-8 relative" style={{ zIndex: 10 }}>
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2
              className="font-bold mb-4 text-2xl md:text-3xl"
              style={{ fontFamily: "'Hanken Grotesk', sans-serif", color: "var(--on-surface)" }}
            >
              How it works
            </h2>
            <p
              className="max-w-2xl mx-auto"
              style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}
            >
              A streamlined pipeline from raw microscopic imagery to actionable environmental
              intelligence.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {howItWorksCards.map((card, i) => (
              <div
                key={i}
                className={`glass-panel rounded-xl p-6 hover:bg-white/5 transition-all duration-300 group cursor-default relative overflow-hidden ${card.mt ?? ""}`}
              >
                {/* Step number watermark */}
                <div
                  className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity"
                  style={{
                    fontFamily: "'Hanken Grotesk', sans-serif",
                    fontSize: "3.75rem",
                    lineHeight: 1,
                    color: "var(--on-surface)",
                  }}
                >
                  {card.step}
                </div>

                {/* Icon circle */}
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center mb-6 transition-shadow"
                  style={{
                    background: "var(--surface-container-high)",
                    border: "1px solid rgba(255,255,255,0.10)",
                    boxShadow: "0 0 15px rgba(255,255,255,0.05)",
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLDivElement).style.boxShadow = `0 0 20px ${card.glowColor}`)
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLDivElement).style.boxShadow =
                      "0 0 15px rgba(255,255,255,0.05)")
                  }
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ color: card.iconColor }}
                  >
                    {card.icon}
                  </span>
                </div>

                <h3
                  className="text-lg font-semibold mb-2"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color: card.titleColor ?? "var(--on-surface)",
                  }}
                >
                  {card.title}
                </h3>
                <p
                  className="text-sm"
                  style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)" }}
                >
                  {card.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
