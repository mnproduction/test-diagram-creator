import { useState, useEffect, useRef } from 'react';

// --- Types ---
interface ProgressUpdate {
  type: string;
  agent: string;
  message: string;
  progress: number;
  timestamp: string;
  session_id: string;
  isVerbose?: boolean;
  metadata?: {
    verbose?: boolean;
    title?: string;
    details?: string;
  };
}

function App() {
  const [description, setDescription] = useState<string>('');
  const [sessionId, setSessionId] = useState<string>('');
  const [progress, setProgress] = useState<ProgressUpdate[]>([]);
  const [diagram, setDiagram] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [isConversationExpanded, setIsConversationExpanded] = useState<boolean>(true);
  const [showScrollToBottom, setShowScrollToBottom] = useState<boolean>(false);
  const ws = useRef<WebSocket | null>(null);
  const conversationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Generate a unique session ID for this client instance
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    setSessionId(newSessionId);
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const connectWebSocket = () => {
      // Use wss for secure connections in production
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Connect to the API server (port 8000), not the frontend dev server (port 5173)
      const apiHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
      const wsUrl = `${wsProtocol}//${apiHost}/ws/diagram-progress/${sessionId}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected to:', wsUrl);
        setWsConnected(true);
      };
      ws.current.onclose = () => {
        console.log('WebSocket disconnected. Attempting to reconnect...');
        setWsConnected(false);
        setTimeout(connectWebSocket, 3000);
      };
      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('WebSocket message received:', message);
          
          if (message.type === 'progress_update' && message.agent && message.message) {
            setProgress(prev => [...prev, {
              ...message,
              isVerbose: message.metadata?.verbose || false
            }]);
          }
        } catch (e) {
          console.error("Failed to parse progress update:", e);
        }
      };
      ws.current.onerror = (err) => console.error('WebSocket error:', err);
    };

    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [sessionId]);

  // Auto-collapse conversation when diagram is ready
  useEffect(() => {
    if (diagram && !isLoading) {
      setIsConversationExpanded(false);
    }
  }, [diagram, isLoading]);

  // Auto-expand conversation when generation starts
  useEffect(() => {
    if (isLoading) {
      setIsConversationExpanded(true);
    }
  }, [isLoading]);

  // Auto-scroll conversation to bottom when new messages arrive
  useEffect(() => {
    if (conversationRef.current && isConversationExpanded) {
      const scrollContainer = conversationRef.current.querySelector('.conversation-scroll');
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: 'smooth'
        });
      }
    }
  }, [progress, isConversationExpanded]);

  // Handle scroll events to show/hide scroll-to-bottom button
  useEffect(() => {
    if (!conversationRef.current || !isConversationExpanded) return;

    const scrollContainer = conversationRef.current.querySelector('.conversation-scroll');
    if (!scrollContainer) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
      const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;
      setShowScrollToBottom(!isNearBottom && scrollHeight > clientHeight);
    };

    scrollContainer.addEventListener('scroll', handleScroll);
    // Initial check
    handleScroll();

    return () => scrollContainer.removeEventListener('scroll', handleScroll);
  }, [isConversationExpanded, progress.length]);

  const scrollToBottom = () => {
    if (conversationRef.current) {
      const scrollContainer = conversationRef.current.querySelector('.conversation-scroll');
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: 'smooth'
        });
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) {
      setError('Please enter a description for the diagram.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setDiagram(null);
    setProgress([]);

    try {
      const response = await fetch('http://localhost:8000/generate-diagram', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'dev-key-1',
        },
        body: JSON.stringify({ description, session_id: sessionId }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data: any = await response.json();

      if (data.success && data.result && data.result.image_data) {
        setDiagram(`data:image/png;base64,${data.result.image_data}`);
      } else {
        setError(data.errors?.join(', ') || 'An unknown error occurred during generation.');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to connect to the server.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleConversation = () => {
    setIsConversationExpanded(!isConversationExpanded);
  };

  const getLatestMessages = () => {
    return progress.slice(-3);
  };



  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50 font-sans">
      {/* Brand Visual Header */}
      <header className="bg-white shadow-lg border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="text-center">
            <div className="inline-flex items-center justify-center space-x-6 mb-4 bg-white rounded-2xl shadow-md px-8 py-4">
              <img src="/engini-logo.svg" alt="Engini" className="h-12 drop-shadow-sm" />
              <img src="/sd-solutions-logo.svg" alt="SD Solutions" className="h-12 drop-shadow-sm" />
              <img src="/mnproduction-logo.svg" alt="MN Production" className="h-12 drop-shadow-sm" />
            </div>
            <h1 className="text-4xl font-bold bg-hero-gradient bg-clip-text text-transparent mb-2">
              AI Diagram Creator
            </h1>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Powered by Engini, SD Solutions & MN Production - Describe your infrastructure and watch our AI agents bring it to life in beautiful diagrams
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        {/* Prompt Section */}
        <section className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-3">
              <label htmlFor="description" className="block text-lg font-semibold text-gray-800 drop-shadow-sm">
                Describe Your Infrastructure
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="e.g., A web application with a load balancer, two web servers, and a database with caching layer"
                className="w-full p-4 text-lg border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:ring-4 focus:ring-purple-100 focus:shadow-lg transition-all duration-200 resize-none min-h-[120px] shadow-sm"
                disabled={isLoading}
                rows={4}
              />
            </div>
            <div className="flex justify-center">
              <button
                type="submit"
                disabled={isLoading || !description.trim()}
                className="group relative px-8 py-4 bg-clickup-gradient text-white font-semibold text-lg rounded-xl shadow-xl hover:shadow-2xl transform hover:scale-105 transition-all duration-200 disabled:opacity-50 disabled:transform-none disabled:cursor-not-allowed min-w-[200px] drop-shadow-md"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center space-x-3">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Generating...</span>
                  </div>
                ) : (
                  <div className="flex items-center justify-center space-x-2">
                    <span>✨ Generate Diagram</span>
                  </div>
                )}
              </button>
            </div>
          </form>
        </section>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <svg className="w-6 h-6 text-red-500 drop-shadow-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-red-800 font-medium drop-shadow-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Agent Conversation */}
        {(progress.length > 0 || isLoading) && (
          <section className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden relative">
            <div 
              className="flex items-center justify-between p-6 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-gray-100 cursor-pointer hover:from-blue-100 hover:to-purple-100 transition-all duration-200 hover:shadow-md"
              onClick={toggleConversation}
            >
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full shadow-md ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                  <h2 className="text-xl font-semibold text-gray-800 drop-shadow-sm">Agent Conversation</h2>
                </div>
                <span className="text-sm text-gray-500 drop-shadow-sm">
                  {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
                </span>
              </div>
              <button className="p-2 hover:bg-white hover:bg-opacity-50 rounded-lg transition-colors duration-200">
                <svg 
                  className={`w-5 h-5 text-gray-600 transform transition-transform duration-200 ${isConversationExpanded ? 'rotate-180' : ''}`} 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
            
            <div 
              ref={conversationRef}
              className={`transition-all duration-300 ease-in-out ${
                isConversationExpanded ? 'h-[500px]' : 'h-24'
              } overflow-hidden`}
            >
              <div className="h-full conversation-scroll scroll-smooth p-6 space-y-4">
                {progress.length === 0 && isLoading && (
                  <div className="flex items-center space-x-3 text-gray-500">
                    <div className="w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
                    <span>Awaiting agent responses...</span>
                  </div>
                )}
                
                {(isConversationExpanded ? progress : getLatestMessages()).map((p, index) => (
                  <div key={index} className={`p-4 rounded-xl border-l-4 transition-all duration-200 shadow-sm hover:shadow-lg ${
                    p.isVerbose 
                      ? 'bg-blue-50 border-l-blue-500 hover:bg-blue-100' 
                      : 'bg-purple-50 border-l-purple-500 hover:bg-purple-100'
                  }`}>
                    <div className="flex items-start space-x-3">
                      <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 shadow-sm ${
                        p.agent === 'ArchitectAgent' ? 'bg-purple-500' :
                        p.agent === 'BuilderAgent' ? 'bg-blue-500' :
                        'bg-green-500'
                      }`}></div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className={`font-semibold text-sm drop-shadow-sm ${
                            p.agent === 'ArchitectAgent' ? 'text-purple-700' :
                            p.agent === 'BuilderAgent' ? 'text-blue-700' :
                            'text-green-700'
                          }`}>
                            {p.agent}
                          </span>
                          {!p.isVerbose && (
                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800 shadow-sm">
                              {p.progress}%
                            </span>
                          )}
                        </div>
                        <p className={`text-sm leading-relaxed ${p.isVerbose ? 'font-mono text-gray-700 bg-gray-50 p-2 rounded' : 'text-gray-800'}`}>
                          {p.message}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(p.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                
                {!isConversationExpanded && progress.length > 3 && (
                  <div className="text-center py-2">
                    <button 
                      onClick={toggleConversation}
                      className="text-sm text-purple-600 hover:text-purple-800 font-medium hover:bg-purple-50 px-3 py-1 rounded-full transition-colors duration-200"
                    >
                      View {progress.length - 3} more messages...
                    </button>
                  </div>
                )}
                
                {/* Scroll indicator when expanded and has many messages */}
                {isConversationExpanded && progress.length > 5 && (
                  <div className="text-center py-2 text-xs text-gray-500">
                    <div className="inline-flex items-center space-x-2 bg-white px-3 py-1 rounded-full shadow-md border drop-shadow-sm">
                      <svg className="w-3 h-3 drop-shadow-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <span className="drop-shadow-sm">Scroll to see all messages</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Scroll to bottom button */}
            {showScrollToBottom && isConversationExpanded && (
              <button
                onClick={scrollToBottom}
                className="absolute bottom-4 right-4 p-3 bg-clickup-gradient text-white rounded-full shadow-lg hover:shadow-xl transform hover:scale-110 transition-all duration-200 z-10"
                title="Scroll to bottom"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </button>
            )}
          </section>
        )}

        {/* Diagram Result */}
        <section className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
          <div className="p-6 bg-gradient-to-r from-green-50 to-blue-50 border-b border-gray-100 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-800 drop-shadow-sm">Generated Diagram</h2>
          </div>
          <div className="p-8">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-4">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin"></div>
                  <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-pink-600 rounded-full animate-spin animate-reverse"></div>
                </div>
                <div className="text-center space-y-2">
                  <p className="text-lg font-medium text-gray-700">Creating your diagram...</p>
                  <p className="text-sm text-gray-500">This may take a few moments</p>
                </div>
              </div>
            ) : diagram ? (
              <div className="space-y-6">
                <div className="relative group">
                  <img 
                    src={diagram} 
                    alt="Generated Infrastructure Diagram" 
                    className="w-full h-auto rounded-xl shadow-xl border border-gray-200 group-hover:shadow-2xl transition-shadow duration-200 drop-shadow-lg"
                  />
                  <div className="absolute inset-0 bg-success-gradient opacity-0 group-hover:opacity-5 rounded-xl transition-opacity duration-200"></div>
                </div>
                <div className="flex justify-center">
                  <div className="inline-flex items-center space-x-2 px-4 py-2 bg-green-100 text-green-800 rounded-full shadow-md">
                    <svg className="w-5 h-5 drop-shadow-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="font-medium drop-shadow-sm">Diagram generated successfully!</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 space-y-4 border-2 border-dashed border-gray-300 rounded-xl shadow-inner">
                <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center shadow-md">
                  <svg className="w-8 h-8 text-gray-400 drop-shadow-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
                <div className="text-center space-y-2">
                  <p className="text-lg font-medium text-gray-700 drop-shadow-sm">Ready to create your diagram</p>
                  <p className="text-sm text-gray-500 drop-shadow-sm">Enter a description above and click generate</p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Credits Footer */}
        <footer className="text-center py-8">
          <div className="inline-flex items-center space-x-3 px-6 py-3 bg-white rounded-full shadow-lg border border-gray-100 drop-shadow-md">
            <span className="text-sm text-gray-600 drop-shadow-sm">Powered by</span>
            <img src="/engini-logo.svg" alt="Engini" className="h-6 drop-shadow-sm" />
            <span className="text-sm text-gray-600 drop-shadow-sm">&</span>
            <img src="/sd-solutions-logo.svg" alt="SD Solutions" className="h-6 drop-shadow-sm" />
            <span className="text-sm text-gray-600 drop-shadow-sm">&</span>
            <img src="/mnproduction-logo.svg" alt="MN Production" className="h-6 drop-shadow-sm" />
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;
