import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'

export default function Portfolio() {
  const [summary, setSummary] = useState<any>(null)
  const [trades,  setTrades]  = useState<any[]>([])
  const [form,    setForm]    = useState({ symbol:'', name:'', action:'BUY', shares:'', price:'', notes:'' })
  const [msg,     setMsg]     = useState('')

  const load = async () => {
    try { setSummary(await api.portfolio.summary()); setTrades(await api.portfolio.trades()) }
    catch { setMsg('Failed to load portfolio data.') }
  }

  useEffect(() => { load() }, [])

  const addTrade = async () => {
    if (!form.symbol || !form.shares || !form.price) { setMsg('Symbol, shares, and price are required.'); return }
    try {
      await api.portfolio.addTrade({ ...form, shares: parseFloat(form.shares), price: parseFloat(form.price) })
      setForm({ symbol:'', name:'', action:'BUY', shares:'', price:'', notes:'' })
      setMsg('Trade added!'); load()
    } catch(e: any) { setMsg(e.message || 'Failed to add trade.') }
  }

  const del = async (id: string) => {
    if (!confirm('Delete this trade?')) return
    await api.portfolio.deleteTrade(id); load()
  }

  const pnlColor = (v: number) => v >= 0 ? 'var(--green)' : 'var(--red)'

  return (
    <div>
      <h1 style={{ fontSize:'1.6rem', marginBottom:'1.5rem' }}>💼 Portfolio</h1>

      {summary && (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(200px,1fr))', gap:'1rem', marginBottom:'1.5rem' }}>
          {[
            { label:'Market Value',    val:`$${summary.total_market_value?.toLocaleString()}` },
            { label:'Total Cost',      val:`$${summary.total_cost?.toLocaleString()}` },
            { label:'Unrealized P&L',  val:`$${summary.total_unrealized_pnl?.toLocaleString()}`, color: pnlColor(summary.total_unrealized_pnl) },
            { label:'Return',          val:`${summary.total_unrealized_pnl_pct?.toFixed(2)}%`, color: pnlColor(summary.total_unrealized_pnl_pct) },
          ].map(s => (
            <div key={s.label} style={card}>
              <div style={{ color:'var(--muted)', fontSize:'0.8rem', marginBottom:'0.3rem' }}>{s.label}</div>
              <div style={{ fontSize:'1.4rem', fontWeight:700, color: s.color || 'var(--text)' }}>{s.val}</div>
            </div>
          ))}
        </div>
      )}

      {summary?.positions?.length > 0 && (
        <div style={{ ...card, marginBottom:'1.5rem', overflowX:'auto' }}>
          <h2 style={h2}>Positions</h2>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'0.88rem' }}>
            <thead><tr>{['Symbol','Name','Shares','Avg Cost','Price','Value','P&L','%'].map(h=><th key={h} style={th}>{h}</th>)}</tr></thead>
            <tbody>
              {summary.positions.map((p: any) => (
                <tr key={p.symbol}>
                  <td style={td}><strong>{p.symbol}</strong></td>
                  <td style={td}>{p.name}</td>
                  <td style={td}>{p.shares}</td>
                  <td style={td}>${p.avg_cost}</td>
                  <td style={td}>${p.current_price}</td>
                  <td style={td}>${p.market_value?.toLocaleString()}</td>
                  <td style={{ ...td, color: pnlColor(p.unrealized_pnl) }}>${p.unrealized_pnl?.toLocaleString()}</td>
                  <td style={{ ...td, color: pnlColor(p.unrealized_pnl_pct) }}>{p.unrealized_pnl_pct?.toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ ...card, marginBottom:'1.5rem' }}>
        <h2 style={h2}>Log Trade</h2>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(160px,1fr))', gap:'0.6rem', marginBottom:'0.8rem' }}>
          {['symbol','name','shares','price','notes'].map(k => (
            <input key={k} placeholder={k.charAt(0).toUpperCase()+k.slice(1)} value={(form as any)[k]}
              onChange={e => setForm(f=>({...f,[k]:e.target.value}))} style={inp} />
          ))}
          <select value={form.action} onChange={e=>setForm(f=>({...f,action:e.target.value}))} style={inp}>
            <option>BUY</option><option>SELL</option>
          </select>
        </div>
        <button onClick={addTrade} style={btn}>+ Add Trade</button>
        {msg && <p style={{ marginTop:'0.5rem', color:'var(--muted)', fontSize:'0.85rem' }}>{msg}</p>}
      </div>

      {trades.length > 0 && (
        <div style={{ ...card, overflowX:'auto' }}>
          <h2 style={h2}>Trade History</h2>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:'0.88rem' }}>
            <thead><tr>{['Date','Symbol','Action','Shares','Price','Total','Notes',''].map(h=><th key={h} style={th}>{h}</th>)}</tr></thead>
            <tbody>
              {trades.map((t: any) => (
                <tr key={t.id}>
                  <td style={td}>{t.date}</td>
                  <td style={td}><strong>{t.symbol}</strong></td>
                  <td style={{ ...td, color: t.action==='BUY'?'var(--green)':'var(--red)' }}>{t.action}</td>
                  <td style={td}>{t.shares}</td>
                  <td style={td}>${t.price}</td>
                  <td style={td}>${t.total?.toLocaleString()}</td>
                  <td style={{ ...td, color:'var(--muted)' }}>{t.notes}</td>
                  <td style={td}><button onClick={()=>del(t.id)} style={{ background:'rgba(239,68,68,.15)', color:'var(--red)', border:'none', padding:'0.25rem 0.6rem', borderRadius:6, cursor:'pointer', fontSize:'0.75rem' }}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const card: React.CSSProperties = { background:'var(--surface)', border:'1px solid var(--border)', borderRadius:12, padding:'1.2rem' }
const h2:   React.CSSProperties = { fontSize:'0.95rem', color:'var(--muted)', marginBottom:'0.8rem', fontWeight:600 }
const th:   React.CSSProperties = { textAlign:'left', padding:'0.5rem 0.8rem', color:'var(--muted)', borderBottom:'1px solid var(--border)', fontWeight:600, fontSize:'0.8rem' }
const td:   React.CSSProperties = { padding:'0.6rem 0.8rem', borderBottom:'1px solid var(--border)' }
const inp:  React.CSSProperties = { background:'var(--bg)', border:'1px solid var(--border)', color:'var(--text)', padding:'0.55rem 0.9rem', borderRadius:8, fontSize:'0.88rem', width:'100%', outline:'none' }
const btn:  React.CSSProperties = { background:'var(--accent)', color:'#fff', border:'none', padding:'0.55rem 1.2rem', borderRadius:8, fontWeight:600, cursor:'pointer' }
