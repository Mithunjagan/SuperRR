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
  const [answer, setAnswer] = useState(null);

  return <section id="analyst" className="rr-section rr-analyst" data-reveal>
    <div className="rr-analyst-intro">
      <h2>Dossier Q&amp;A</h2>
      <p>Answers on the bowling rankings, the pace bid, and the 2026 forecast check.</p>
    </div>
    <div className="rr-analyst-card">
      <div className="rr-analyst-examples" role="group" aria-label="Dossier answers">
        {examples.map(item => <button type="button" key={item.label} aria-pressed={answer === item} onClick={() => setAnswer(item)}>{item.label}</button>)}
      </div>
      <div aria-live="polite">
        {answer && <div className="rr-analyst-answer"><p>{answer.answer}</p></div>}
      </div>
    </div>
  </section>;
}

