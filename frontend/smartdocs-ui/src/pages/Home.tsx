import { useState } from "react";
import { UploadDocument } from "../components/UploadDocument";
import { Link } from "react-router-dom";

export function Home() {
  const [docId, setDocId] = useState<string | null>(null);

  return (
    <div className="space-y-20 fade-in">
      {/* Hero Section */}
      <section className="relative pt-4 md:pt-10">
        <div className="absolute inset-0 -z-10 hero-glow pointer-events-none" />
        <div className="space-y-8">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-600/10 ring-1 ring-brand-500/30 text-[0.65rem] font-medium tracking-wide text-brand-200 slide-up">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400 animate-pulse" />{" "}
              EARLY PREVIEW
            </div>
            <h1 className="text-5xl md:text-6xl font-semibold tracking-tight leading-[1.05] gradient-text slide-up">
              Conversational Intelligence
              <br className="hidden md:block" />
              for Your Documents
            </h1>
            <p className="text-neutral-300 text-base md:text-lg max-w-2xl leading-relaxed slide-up">
              SmartDocs lets you upload technical or business documents and then
              interact with them through an AI-driven conversational interface.
              Ask contextual questions, extract insights, and accelerate
              understanding.
            </p>
            <div className="flex flex-wrap gap-3 slide-up">
              <Link to="/chat" state={{ docId }} className="btn">
                Open Chat {docId ? "with Document" : ""}
              </Link>
              <a
                href="https://react.dev"
                target="_blank"
                rel="noreferrer"
                className="btn-outline"
              >
                React Docs
              </a>
            </div>
          </div>

          {/* Upload Panel */}
          <div className="grid md:grid-cols-[1fr_minmax(0,420px)] gap-10 items-start slide-up">
            <div className="space-y-10">
              <UploadDocument onUploaded={setDocId} />

              {docId && (
                <div className="text-xs text-brand-300 flex items-center gap-2">
                  <span className="badge">Document Ready</span>
                  <span className="text-brand-200">ID:</span>
                  <code className="text-brand-100">{docId}</code>
                </div>
              )}

              <div className="grid sm:grid-cols-3 gap-4">
                {[
                  {
                    title: "Semantic Chat",
                    desc: "Context-aware answers grounded in your uploaded material."
                  },
                  {
                    title: "Fast Iteration",
                    desc: "Upload & query within seconds—no heavy preprocessing yet."
                  },
                  {
                    title: "Extensible API",
                    desc: "Designed to integrate with your knowledge pipelines."
                  }
                ].map((f) => (
                  <div
                    key={f.title}
                    className="card p-4 space-y-2 hover:shadow-brand-glow transition-shadow"
                  >
                    <h3 className="text-sm font-semibold">{f.title}</h3>
                    <p className="text-[0.7rem] leading-relaxed text-neutral-400">
                      {f.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Side Info Panel */}
            <aside className="card relative overflow-hidden">
              <div className="absolute inset-0 pointer-events-none bg-grid-radial opacity-40" />
              <div className="relative space-y-6">
                <h2 className="text-xl font-semibold gradient-text">
                  How it Works
                </h2>
                <ol className="space-y-4 text-sm text-neutral-300">
                  <li className="flex gap-3">
                    <span className="h-6 w-6 rounded-full bg-brand-600 text-white text-xs flex items-center justify-center font-medium">
                      1
                    </span>
                    <p>
                      Upload a PDF or text-based document. (Demo currently mocks
                      an ID.)
                    </p>
                  </li>
                  <li className="flex gap-3">
                    <span className="h-6 w-6 rounded-full bg-brand-600 text-white text-xs flex items-center justify-center font-medium">
                      2
                    </span>
                    <p>
                      Open the chat interface to begin asking contextual
                      questions.
                    </p>
                  </li>
                  <li className="flex gap-3">
                    <span className="h-6 w-6 rounded-full bg-brand-600 text-white text-xs flex items-center justify-center font-medium">
                      3
                    </span>
                    <p>
                      Iterate rapidly—answers refine as the intelligence layer
                      evolves.
                    </p>
                  </li>
                </ol>
                <div className="pt-2">
                  <Link
                    to="/chat"
                    state={{ docId }}
                    className="btn w-full justify-center"
                  >
                    Start Chatting
                  </Link>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>

      {/* Page-specific footer removed to rely on global footer in App layout */}
    </div>
  );
}
