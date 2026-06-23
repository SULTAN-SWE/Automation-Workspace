import React, { useState, useRef, useEffect } from 'react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function App() {
  const [email, setEmail] = useState('');
  const [token, setToken] = useState(localStorage.getItem('eaap_token') || '');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const login = async (e) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: 'demo' })
    });
    const data = await res.json();
    if (data.access_token) {
      setToken(data.access_token);
      localStorage.setItem('eaap_token', data.access_token);
    } else {
      alert('Login failed');
    }
  };

  const logout = () => {
    setToken('');
    localStorage.removeItem('eaap_token');
    setMessages([]);
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ message: userMsg, session_id: localStorage.getItem('eaap_session') })
      });
      const data = await res.json();
      if (data.session_id) {
        localStorage.setItem('eaap_session', data.session_id);
      }
      const reply = data.response || data.message || JSON.stringify(data);
      setMessages(prev => [...prev, { role: 'assistant', content: reply, meta: data }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div style={{ maxWidth: 420, margin: '80px auto', padding: 24, border: '1px solid #ccc', borderRadius: 8, fontFamily: 'sans-serif' }}>
        <h2>Enterprise AI Agent Platform</h2>
        <p>Sign in with any email to access the Master AI Agent.</p>
        <form onSubmit={login}>
          <input
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={{ width: '100%', padding: 10, marginBottom: 12, boxSizing: 'border-box' }}
            required
          />
          <button type="submit" style={{ width: '100%', padding: 10, cursor: 'pointer' }}>Login</button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', fontFamily: 'sans-serif' }}>
      <header style={{ padding: '12px 24px', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <strong>Enterprise AI Agent Platform</strong>
          <span style={{ marginLeft: 12, color: '#666', fontSize: 12 }}>Master AI Agent Orchestrator</span>
        </div>
        <button onClick={logout} style={{ padding: '6px 12px', cursor: 'pointer' }}>Logout</button>
      </header>
      <div style={{ flex: 1, overflowY: 'auto', padding: 24, background: '#f5f5f5' }}>
        {messages.length === 0 && <p style={{ color: '#888' }}>Ask the Master AI Agent anything. Examples: "Request PTO next week", "Create an IT ticket", "What is the remote work policy?"</p>}
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 16, textAlign: m.role === 'user' ? 'right' : 'left' }}>
            <div style={{
              display: 'inline-block',
              padding: '12px 16px',
              borderRadius: 12,
              background: m.role === 'user' ? '#0078d4' : '#fff',
              color: m.role === 'user' ? '#fff' : '#222',
              maxWidth: '70%',
              whiteSpace: 'pre-wrap'
            }}>
              {m.content}
            </div>
            {m.meta && m.meta.status === 'pending_approval' && (
              <div style={{ fontSize: 12, color: '#d46b08', marginTop: 4 }}>Pending manager approval</div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={sendMessage} style={{ padding: 16, borderTop: '1px solid #eee', display: 'flex', background: '#fff' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type your request..."
          style={{ flex: 1, padding: 12, marginRight: 12, borderRadius: 4, border: '1px solid #ccc' }}
          disabled={loading}
        />
        <button type="submit" disabled={loading} style={{ padding: '12px 24px', cursor: loading ? 'not-allowed' : 'pointer' }}>
          {loading ? '...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
