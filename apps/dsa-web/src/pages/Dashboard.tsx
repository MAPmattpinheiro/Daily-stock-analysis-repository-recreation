import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'

const ICONS: Record<string,string> = { BUY:'🟢', WATCH:'🟡', SELL:'🔴' }

export default function Dashboard() {
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus]   = useState('')

  useEffect(() => { api.results().then(setResults).catch(()=>{}) }, [])

  const analyze = async (syms = '') => {
    setLoading(true); setStatus('⏳ Analyzing... this may take 1–2 minutes.')
    try { await api.analyze(syms); const r = await api.results(); setResults(r); setStatus('✅ Done!') }
    catch { setStatus('❌ Failed') } finally { setLoading(false) }
  }

  const notify = async () => {
    try { await api.notify(); setStatus('📤 Notifications sent!') }
    catch { setStatus('❌ Notification failed') }
  }

  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1.5rem' }}>
        <h1 style={{ fontSize:'1.6rem' }}>📈 Dashboard</h1>
        <div style={{ display:'flex', gap:'0.6rem' }}>
          <Btn secondary onClick={() => analyze()}>↺ Re-run</Btn>
          <Btn onClick={notify}>📤 Send</Btn>
        </div>
      </div>

      {results.length > 0 && (
        <div style={{ ...card, display:'flex', gap:'2rem', padding:'1rem 1.5rem', marginBottom:'1.5rem' }}>
          <span>🟢 Buy: <strong>{results.filter(r=>r.signal==='BUY').length}</strong></span>
          <span>🟡 Watch: <strong>{results.filter(r=>r.signal==='WATCH').length}</strong></span>
          <span>🔴 Sell: <strong>{results.filter(r=>r.signal==='SELL').length}</strong></span>
        </div>
      )}

      {results.length === 0 && !loading && (
        <div style={{ ...card, color:'var(--muted)' }}>No results yet. Run an analysis to get started.</div>
      )}

      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(280px,1fr))', gap:'1rem', marginBottom:'1.5rem' }}>
        {results.map(r => <StockCard key={r.symbol} r={r} />)}
      </div>

      <div style={card}>
        <h2 style={{ fontSize:'1rem', color:'var(--muted)', marginBottom:'0.8rem' }}>Run Analysis</h2>
        <div style={{ display:'flex', gap:'0.6rem' }}>
          <input id="syms" placeholder="Symbols e.g. AAPL,TSLA (blank = saved list)" style={input} />
          <Btn onClick={() => analyze((document.getElementById('syms') as HTMLInputElement).value)} disabled={loading}>▶ Analyze</Btn>
        </div>
        {status && <p style={{ marginTop:'0.6rem', color:'var(--muted)', fontSize:'0.85rem' }}>{status}</p>}
      </div>
    </div>
  )
}

function StockCard({ r }: { r: any }) {
  const sig = (r.signal||'WATCH').toLowerCase()
  const chg = r.change_pct ?? 0
  const badgeColor: Record<string,string> = { buy:'var(--green)', watch:'var(--yellow)', sell:'var(--red)' }
  return (
    <div style={{ ...card, transition:'border-color .2s' }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'0.8rem' }}>
        <div>
          <div style={{ fontWeight:700, fontSize:'1.1rem' }}>{r.symbol}</div>
          <div style={{ fontSize:'0.78rem', color:'var(--muted)' }}>{r.name}</div>
        </div>
        <span style={{ background:`color-mix(in srgb,${badgeColor[sig]} 15%,transparent)`, color:badgeColor[sig], padding:'0.2rem 0.7rem', borderRadius:20, fontSize:'0.75rem', fontWeight:700, height:'fit-content' }}>{r.signal}</span>
      </div>
      <div style={{ display:'flex', gap:'0.5rem', alignItems:'baseline', marginBottom:'0.6rem' }}>
        <span style={{ fontSize:'1.25rem', fontWeight:600 }}>${r.price}</span>
        <span style={{ color: chg>=0?'var(--green)':'var(--red)', fontSize:'0.88rem' }}>{chg>=0?'+':''}{chg?.toFixed(2)}%</span>
      </div>
      <p style={{ fontSize:'0.83rem', color:'var(--muted)', lineHeight:1.5, marginBottom:'0.8rem' }}>{r.conclusion}</p>
      <div style={{ height:4, background:'var(--border)', borderRadius:2, overflow:'hidden' }}>
        <div style={{ height:'100%', width:`${r.score}%`, background:'var(--accent)', borderRadius:2 }} />
      </div>
      <div style={{ fontSize:'0.75rem', color:'var(--muted)', marginTop:4 }}>Score: {r.score}/100 | {r.outlook}</div>
    </div>
  )
}

function Btn({ children, onClick, secondary, disabled }: any) {
  return <button onClick={onClick} disabled={disabled} style={{ background: secondary?'var(--border)':'var(--accent)', color: secondary?'var(--text)':'#fff', border:'none', padding:'0.55rem 1.2rem', borderRadius:8, fontWeight:600, cursor:'pointer', opacity: disabled ? 0.6 : 1 }}>{children}</button>
}
const card: React.CSSProperties = { background:'var(--surface)', border:'1px solid var(--border)', borderRadius:12, padding:'1.2rem' }
const input: React.CSSProperties = { flex:1, background:'var(--bg)', border:'1px solid var(--border)', color:'var(--text)', padding:'0.55rem 1rem', borderRadius:8, fontSize:'0.9rem', outline:'none' }
