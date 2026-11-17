import React, { useState } from "react";

const examples = [
  {
    label:"Why is Hosein #1?",
    answer:"Hosein leads the official bowling ranking because his worst leave-one-match-out score is 22.10 versus Bumrah’s 21.66. He was positive in 15 of 19 matches, compared with Bumrah’s 16 of 24. The 0.44-point gap is small. Bumrah leads on bootstrap Q25, chase-only rank, and IPL exposure. See the dossier, page 6."
  },
  {
    label:"Who is the pace bid?",
    answer:"If Archer leaves and Bumrah enters the official auction pool, Bumrah is the first pace bid. He covers the new ball plus the death and has 113 qualifying IPL balls. Shami adds new-ball pace, so closing overs are the priority. See pages 1, 8 and 10."
  },
  {
    label:"Did it predict 2026?",
    answer:"The zero baseline had lower forecast RMSE in both roles. Batters: 44.69 versus 50.43 for the final rating. Bowlers: 43.69 versus 47.02. The 2026 period was inspected repeatedly and is not an untouched confirmation sample. See page 7."
  }
];

export default function Analyst() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  async function ask(event) {
    event.preventDefault();
    const prompt = question.trim();
    if (!prompt || loading) return;
    setLoading(true);
    setAnswer(null);
    try {
      const response = await fetch("/api/analyst", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({question:prompt}),
        signal:AbortSignal.timeout(18000)
      });
      const data = await response.json();
      if (response.ok && typeof data.answer === "string") {
        setAnswer({label:"Gemini · dossier-grounded answer", text:data.answer});
      } else {
        setAnswer({label:"Live analyst unavailable",text:data.error || "Try a dossier answer above."});
      }
    } catch {
      setAnswer({label:"Live analyst unavailable",text:"Try one of the dossier answers above."});
    } finally {
      setLoading(false);
    }
  }

  return <section id="analyst" className="rr-section rr-analyst" data-reveal>
    <div className="rr-analyst-intro">
      <div className="rr-kicker"><span/> REPORT Q&A</div>
      <h2>Ask the Analyst<span>.</span></h2>
      <p>Ask why a player ranked where they did, how pressure was measured, or what could change an RR bid.</p>
    </div>
    <div className="rr-analyst-card">
      <div className="rr-analyst-examples" role="group" aria-label="Dossier answers">
        {examples.map(item => <button type="button" key={item.label} disabled={loading} onClick={() => setAnswer({label:"Dossier answer", text:item.answer})}>{item.label}<span aria-hidden="true"> ↗</span></button>)}
      </div>
      <form onSubmit={ask}>
        <label htmlFor="rr-question">Ask a question about the analysis</label>
        <div className="rr-analyst-input">
          <input id="rr-question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={320} placeholder="e.g. How is own-baseline lift different from the final rating?" required/>
          <button type="submit" disabled={loading || !question.trim()}>{loading ? "Asking…" : "Ask Gemini"} <span aria-hidden="true">↗</span></button>
        </div>
      </form>
      <div aria-live="polite" aria-busy={loading}>
        {loading && <p className="rr-analyst-status">Checking the dossier evidence…</p>}
        {answer && <div className="rr-analyst-answer"><strong>{answer.label}</strong><p>{answer.text}</p></div>}
      </div>
    </div>
  </section>;
}

