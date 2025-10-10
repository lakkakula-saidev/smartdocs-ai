import { Routes, Route, Link, NavLink } from "react-router-dom";
import { Home } from "./pages/Home";
import { Chat } from "./pages/Chat";

export default function App() {
  return (
    <div className="relative min-h-screen flex flex-col">
      {/* Global decorative background grid / glow overlay */}
      <div
        className="pointer-events-none fixed inset-0 hero-glow opacity-70"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_10%_10%,rgba(43,165,255,0.12),transparent_60%)]"
        aria-hidden="true"
      />

      {/* Top Navigation */}
      <header className="sticky top-0 z-40 backdrop-blur-sm bg-neutral-950/70 border-b border-white/5">
        <nav className="mx-auto max-w-7xl px-6 md:px-10 h-14 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-2 group"
            aria-label="SmartDocs Home"
          >
            <span className="relative flex h-7 w-7 items-center justify-center">
              <span className="absolute inset-0 rounded-md bg-gradient-to-br from-brand-400 via-brand-500 to-brand-600 opacity-90 group-hover:opacity-100 transition shadow-brand-glow" />
              <span className="relative text-[0.55rem] font-bold tracking-wider text-white select-none">
                SD
              </span>
            </span>
            <span className="font-semibold tracking-tight text-neutral-100 group-hover:text-white transition">
              SmartDocs
            </span>
          </Link>

          <ul className="flex items-center gap-6 text-sm">
            <li>
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `transition-colors ${
                    isActive
                      ? "text-brand-300"
                      : "text-neutral-400 hover:text-neutral-200"
                  }`
                }
              >
                Home
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/chat"
                className={({ isActive }) =>
                  `transition-colors ${
                    isActive
                      ? "text-brand-300"
                      : "text-neutral-400 hover:text-neutral-200"
                  }`
                }
              >
                Chat
              </NavLink>
            </li>
            <li>
              <a
                href="https://react.dev"
                target="_blank"
                rel="noreferrer"
                className="text-neutral-400 hover:text-neutral-200 transition-colors"
              >
                React Docs
              </a>
            </li>
            <li>
              <a
                href="https://tailwindcss.com"
                target="_blank"
                rel="noreferrer"
                className="text-neutral-400 hover:text-neutral-200 transition-colors"
              >
                Tailwind
              </a>
            </li>
          </ul>
        </nav>
      </header>

      {/* Main routed content (flex column + min-h-0 so nested pages (e.g. Chat) can establish internal scroll without pushing footer) */}
      <main className="flex-1 min-h-0 flex flex-col w-full mx-auto max-w-7xl px-6 md:px-10 py-10 md:py-14">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </main>

      {/* Global Footer */}
      <footer className="mt-auto border-t border-white/5 bg-neutral-950/60 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-6 md:px-10 py-6 flex flex-col md:flex-row gap-4 md:items-center md:justify-between text-[0.7rem] text-neutral-500">
          <p>
            &copy; {new Date().getFullYear()} SmartDocs AI • Built with React,
            Vite & Tailwind
          </p>
          <p className="flex gap-3">
            <a
              href="https://github.com/"
              className="hover:text-brand-300 transition-colors"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
            <a
              href="https://react.dev"
              className="hover:text-brand-300 transition-colors"
              target="_blank"
              rel="noreferrer"
            >
              React
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
