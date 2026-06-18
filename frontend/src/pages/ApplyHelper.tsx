import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Send, Loader2, Bot, User } from "lucide-react";
import { api } from "../api";
import type { Grant, ChatMessage } from "../types";

export default function ApplyHelper() {
  const { grantId } = useParams<{ grantId?: string }>();
  const navigate = useNavigate();

  const [grants, setGrants] = useState<Grant[]>([]);
  const [selectedGrant, setSelectedGrant] = useState<Grant | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load grants list
  useEffect(() => {
    api.listGrants().then(setGrants).catch(console.error);
  }, []);

  // Auto-select grant from URL param
  useEffect(() => {
    if (grantId && grants.length > 0) {
      const g = grants.find((g) => g.id === parseInt(grantId));
      if (g) setSelectedGrant(g);
    }
  }, [grantId, grants]);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const selectGrant = (grant: Grant) => {
    setSelectedGrant(grant);
    setSessionId(null);
    setMessages([]);
    setError(null);
    navigate(`/apply/${grant.id}`, { replace: true });
  };

  const sendMessage = async () => {
    if (!selectedGrant || !input.trim() || thinking) return;
    const userMsg = input.trim();
    setInput("");
    setThinking(true);
    setError(null);

    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);

    try {
      const res = await api.sendChat(selectedGrant.id, userMsg, sessionId ?? undefined);
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (e) {
      setError(String(e));
    } finally {
      setThinking(false);
    }
  };

  const startFresh = () => {
    setSessionId(null);
    setMessages([]);
    setError(null);
    setInput("");
  };

  // Starter prompts
  const starters = [
    "What information do I need to gather for this application?",
    "Help me write a project description",
    "What does this funder look for in applications?",
    "How much should I ask for?",
  ];

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      {/* Grant selector panel */}
      <div className="w-72 shrink-0 flex flex-col">
        <h2 className="font-semibold text-gray-800 mb-3 text-sm uppercase tracking-wide">
          Select a Grant
        </h2>
        {grants.length === 0 ? (
          <p className="text-sm text-gray-400">
            No grants yet — search for some first.
          </p>
        ) : (
          <div className="space-y-2 overflow-y-auto flex-1 pr-1">
            {grants.map((g) => (
              <button
                key={g.id}
                onClick={() => selectGrant(g)}
                className={`w-full text-left p-3 rounded-lg border text-sm transition-colors ${
                  selectedGrant?.id === g.id
                    ? "bg-leaf-100 border-leaf-400 text-leaf-900"
                    : "bg-white border-gray-200 text-gray-700 hover:bg-leaf-50 hover:border-leaf-300"
                }`}
              >
                <div className="font-medium leading-snug line-clamp-2">{g.title}</div>
                <div className="text-xs text-gray-500 mt-0.5">{g.funder}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Chat panel */}
      <div className="flex-1 flex flex-col bg-white rounded-xl border border-leaf-200 shadow-sm overflow-hidden">
        {/* Header */}
        <div className="border-b border-leaf-100 px-5 py-3 flex items-center gap-3">
          {selectedGrant ? (
            <>
              <div className="flex-1 min-w-0">
                <h2 className="font-semibold text-gray-900 truncate">
                  {selectedGrant.title}
                </h2>
                <p className="text-xs text-gray-500">{selectedGrant.funder}</p>
              </div>
              <button
                onClick={startFresh}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                New chat
              </button>
            </>
          ) : (
            <h2 className="font-semibold text-gray-400">
              ← Select a grant to get started
            </h2>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && selectedGrant && (
            <div className="py-6">
              <div className="flex items-center gap-2 mb-3">
                <Bot className="w-5 h-5 text-leaf-600" />
                <p className="text-sm text-gray-600 font-medium">
                  Hi! I'm here to help you apply for{" "}
                  <strong>{selectedGrant.title}</strong>. Where would you like
                  to start?
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {starters.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      setInput(s);
                    }}
                    className="text-left text-xs p-2.5 bg-leaf-50 hover:bg-leaf-100 border border-leaf-200 rounded-lg text-leaf-700 transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : ""}`}
            >
              {msg.role === "assistant" && (
                <div className="w-6 h-6 rounded-full bg-leaf-600 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-leaf-600 text-white rounded-tr-sm"
                    : "bg-gray-100 text-gray-800 rounded-tl-sm"
                }`}
              >
                {msg.content}
              </div>
              {msg.role === "user" && (
                <div className="w-6 h-6 rounded-full bg-leaf-200 flex items-center justify-center shrink-0 mt-1">
                  <User className="w-3.5 h-3.5 text-leaf-700" />
                </div>
              )}
            </div>
          ))}

          {thinking && (
            <div className="flex gap-2.5">
              <div className="w-6 h-6 rounded-full bg-leaf-600 flex items-center justify-center shrink-0">
                <Bot className="w-3.5 h-3.5 text-white" />
              </div>
              <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
                <Loader2 className="w-4 h-4 animate-spin text-leaf-600" />
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              Error: {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-leaf-100 p-4">
          {!selectedGrant ? (
            <p className="text-sm text-center text-gray-400">
              Select a grant from the left to start chatting
            </p>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                placeholder="Ask about the application…"
                disabled={thinking}
                className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-leaf-400 disabled:opacity-50"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim() || thinking}
                className="p-2.5 bg-leaf-600 text-white rounded-xl hover:bg-leaf-700 disabled:opacity-40 transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
