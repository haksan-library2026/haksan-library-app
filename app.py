/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import Papa from 'papaparse';
import { GoogleGenAI, Type } from "@google/genai";
import { motion, AnimatePresence } from 'motion/react';
import { Book, Heart, Sparkles, Send, Loader2, Library, RefreshCcw, ImagePlus, X, User, Headphones, Play, Pause, Mic2, MessageCircle, MessageSquare } from 'lucide-react';

// Book type definition
interface LibraryBook {
  title: string;
  author: string;
  category: string;
  description: string;
}

interface Recommendation {
  title: string;
  reason: string;
  protagonist: string;
  personality: string;
}

interface ChatMessage {
  role: 'user' | 'model';
  text: string;
}

interface PodcastTurn {
  speaker: '준호' | '민지';
  text: string;
}

interface AiResponse {
  recommendations: Recommendation[];
  characterPrompt: string;
  podcastScript: PodcastTurn[];
}

export default function App() {
  const [books, setBooks] = useState<LibraryBook[]>([]);
  const [mood, setMood] = useState('');
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [generatedCharacterUrl, setGeneratedCharacterUrl] = useState<string | null>(null);
  const [podcastScript, setPodcastScript] = useState<PodcastTurn[]>([]);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isAudioLoading, setIsAudioLoading] = useState(false);
  const [isCsvLoading, setIsCsvLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Chat States
  const [activeChatBook, setActiveChatBook] = useState<Recommendation | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Initialize Gemini API
  const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Load Library Data
  useEffect(() => {
    const loadCsv = async () => {
      try {
        const response = await fetch('/library_list.csv');
        if (!response.ok) throw new Error('파일을 찾을 수 없습니다.');
        const csvData = await response.text();
        
        Papa.parse(csvData, {
          header: true,
          complete: (results) => {
            setBooks(results.data as LibraryBook[]);
            setIsCsvLoading(false);
          },
          error: (err: Error) => {
            console.error('CSV Parsing Error:', err);
            setError('도서 목록을 불러오는 데 실패했습니다.');
            setIsCsvLoading(false);
          }
        });
      } catch (err: any) {
        console.error('Fetch Error:', err);
        setError('서버에서 데이터를 가져오지 못했습니다: ' + err.message);
        setIsCsvLoading(false);
      }
    };

    loadCsv();
  }, []);

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const generatePodcastAudio = async (script: PodcastTurn[]) => {
    setIsAudioLoading(true);
    try {
      const scriptText = script.map(turn => `${turn.speaker}: ${turn.text}`).join('\n');
      const response = await ai.models.generateContent({
        model: "gemini-3.1-flash-tts-preview",
        contents: [{ parts: [{ text: `Generate a natural podcast conversation based on this script:\n${scriptText}` }] }],
        config: {
          responseModalities: ['AUDIO'],
          speechConfig: {
            multiSpeakerVoiceConfig: {
              speakerVoiceConfigs: [
                {
                  speaker: '준호',
                  voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } } // Deep/Male
                },
                {
                  speaker: '민지',
                  voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Puck' } } // Friendly/Female
                }
              ]
            }
          }
        }
      });

      const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      if (base64Audio) {
        const binary = atob(base64Audio);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
      }
    } catch (err) {
      console.error('TTS Error:', err);
    } finally {
      setIsAudioLoading(false);
    }
  };

  const getRecommendations = async () => {
    if (!mood.trim() && !selectedImage) return;
    
    setIsLoading(true);
    setError(null);
    setRecommendations([]);
    setGeneratedCharacterUrl(null);
    setPodcastScript([]);
    setAudioUrl(null);
    setIsPlaying(false);
    setActiveChatBook(null);
    setChatMessages([]);

    try {
      const bookContext = books
        .map((b) => `제목: ${b.title}, 저자: ${b.author}, 카테고리: ${b.category}, 설명: ${b.description}`)
        .join('\n');

      const parts: any[] = [
        {
          text: `학생의 기분글: "${mood}"
사용 가능한 도서 목록:
${bookContext}

위 목록에서 학생의 기분과 (만약 이미지가 있다면) 이미지의 분위기를 분석해서 어울리는 책을 3권 이내로 추천해줘.
1. 추천 도서 정보 (제목과 따뜻한 사서 선생님 말투의 이유)
2. 추천 도서의 주인공 이름 1명(없으면 지어내기)과 그 주인공의 성격(말투, 특징 1-2문장)
3. 추천 도서 분위기에 맞는 지브리 스타일 캐릭터 프롬프트 (영어)
4. 준호와 민지라는 두 친구가 이 책들에 대해 수다 떠는 팟캐스트 짧은 대본 (4-6문장 내외). 
   말투는 아주 실감 나고 "대박", "헐", "진짜 대박이야", "꼭 읽어봐야 해" 같은 자연스러운 구어체여야 함.
천천히 생각해서 모든 정보를 JSON으로 줘.`
        }
      ];

      if (selectedImage) {
        const base64Data = selectedImage.split(',')[1];
        parts.push({
          inlineData: {
            mimeType: "image/jpeg",
            data: base64Data
          }
        });
      }

      const response = await ai.models.generateContent({
        model: "gemini-3-flash-preview",
        contents: { parts },
        config: {
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              recommendations: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    title: { type: Type.STRING },
                    reason: { type: Type.STRING },
                    protagonist: { type: Type.STRING, description: "주인공 이름" },
                    personality: { type: Type.STRING, description: "주인공의 성격 및 말투 묘사" }
                  },
                  required: ["title", "reason", "protagonist", "personality"]
                }
              },
              characterPrompt: { type: Type.STRING },
              podcastScript: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    speaker: { type: Type.STRING, enum: ["준호", "민지"] },
                    text: { type: Type.STRING }
                  },
                  required: ["speaker", "text"]
                }
              }
            },
            required: ["recommendations", "characterPrompt", "podcastScript"]
          }
        }
      });

      if (response.text) {
        const result: AiResponse = JSON.parse(response.text);
        setRecommendations(result.recommendations);
        setPodcastScript(result.podcastScript);
        
        generatePodcastAudio(result.podcastScript);
        
        if (result.characterPrompt) {
          try {
            const imageResponse = await ai.models.generateContent({
              model: 'gemini-2.5-flash-image',
              contents: { parts: [{ text: result.characterPrompt }] }
            });
            for (const part of imageResponse.candidates[0].content.parts) {
              if (part.inlineData) {
                setGeneratedCharacterUrl(`data:image/png;base64,${part.inlineData.data}`);
                break;
              }
            }
          } catch (imgErr) {
            console.error('Image Generation Error:', imgErr);
          }
        }
      }
    } catch (err) {
      console.error('Gemini API Error:', err);
      setError('AI가 추천을 생성하는 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const startChat = (book: Recommendation) => {
    setActiveChatBook(book);
    setChatMessages([
      { role: 'model', text: `안녕! 나는 '${book.title}'의 ${book.protagonist}(이)야. 반가워!` }
    ]);
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || !activeChatBook || isChatLoading) return;

    const userMessage = { role: 'user' as const, text: chatInput };
    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsChatLoading(true);

    try {
      const systemPrompt = `You are ${activeChatBook.protagonist}, a character from the book "${activeChatBook.title}". 
Your personality and way of speaking are: ${activeChatBook.personality}.
Answer the student's messages as this character. Keep your answers brief and in character. Do not break character. 
Write in Korean.`;

      const response = await ai.models.generateContent({
        model: "gemini-3-flash-preview",
        contents: [
          { role: 'user', parts: [{ text: systemPrompt }] },
          { role: 'model', parts: [{ text: "알겠어. 내가 그 캐릭터가 되어 대답할게." }] },
          ...chatMessages.map(msg => ({
            role: msg.role,
            parts: [{ text: msg.text }]
          })),
          { role: 'user', parts: [{ text: chatInput }] }
        ]
      });

      const modelText = response.text || "미안, 지금은 대답하기 어려워.";
      setChatMessages(prev => [...prev, { role: 'model', text: modelText }]);
    } catch (err) {
      console.error('Chat Error:', err);
      setChatMessages(prev => [...prev, { role: 'model', text: "미안, 도서관 통신이 잠시 불안정한 것 같아." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col items-center justify-start max-w-4xl mx-auto">
      {/* Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="inline-block p-3 bg-ghibli-sage rounded-full mb-4 shadow-sm">
          <Library className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-4xl font-serif font-bold text-ghibli-brown mb-2">지브리 도서관 추천봇</h1>
        <p className="text-ghibli-brown/70 font-sans tracking-wide">
          사진과 마음, 그리고 목소리가 담긴 당신만의 도서 추천 서비스.
        </p>
      </motion.header>

      {/* Main Content */}
      <main className="w-full space-y-8 pb-32">
        <motion.div 
          className="ghibli-card p-6 md:p-8 flex flex-col gap-8 shadow-inner bg-ghibli-cream/80"
          layout
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-6">
              <div className="space-y-4">
                <label className="text-lg font-serif font-medium flex items-center gap-2">
                  <Heart className="w-5 h-5 text-red-400" />
                  오늘의 기분은 어떤가요?
                </label>
                <textarea
                  className="w-full p-4 rounded-xl border border-ghibli-sandy bg-white/60 focus:ring-2 focus:ring-ghibli-sage focus:outline-none transition-all placeholder:text-ghibli-brown/30 min-h-[140px] font-sans text-ghibli-brown"
                  placeholder="예: 지친 마음을 달래줄 포근한 이야기가 필요해요."
                  value={mood}
                  onChange={(e) => setMood(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-4">
              <label className="text-lg font-serif font-medium flex items-center gap-2">
                <ImagePlus className="w-5 h-5 text-blue-400" />
                분위기를 담은 사진 (선택)
              </label>
              <div className="relative h-[140px]">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  ref={fileInputRef}
                  onChange={handleImageUpload}
                />
                {!selectedImage ? (
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full h-full border-2 border-dashed border-ghibli-sandy rounded-xl flex flex-col items-center justify-center gap-2 text-ghibli-brown/40 hover:bg-white/40 transition-colors"
                  >
                    <Mic2 className="w-8 h-8 opacity-20 absolute -z-10 blur-[1px]" />
                    <ImagePlus className="w-8 h-8" />
                    <span className="text-sm font-sans">사진을 올려주세요</span>
                  </button>
                ) : (
                  <div className="relative w-full h-full">
                    <img src={selectedImage} alt="Selected" className="w-full h-full object-cover rounded-xl border border-ghibli-sandy shadow-sm" />
                    <button onClick={clearImage} className="absolute -top-2 -right-2 p-1 bg-white border border-ghibli-sandy rounded-full shadow-md text-red-500 hover:bg-red-50">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={getRecommendations}
            disabled={isLoading || isCsvLoading || (!mood.trim() && !selectedImage)}
            className="ghibli-button w-full py-4 rounded-xl font-serif font-bold text-lg flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                선생님과 친구들이 준비 중이에요...
              </>
            ) : (
              <><Send className="w-5 h-5" /> 추천받기</>
            )}
          </button>
        </motion.div>

        {/* Results Sections */}
        <AnimatePresence mode="wait">
          {(recommendations.length > 0 || generatedCharacterUrl || podcastScript.length > 0) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-10">
              
              {/* Podcast Section */}
              {podcastScript.length > 0 && (
                <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="ghibli-card p-6 bg-ghibli-sage/10 border-ghibli-sage/30">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3 text-ghibli-brown">
                      <Headphones className="w-6 h-6" />
                      <h2 className="text-xl font-serif font-bold italic">Short Talk! 한줄 대화</h2>
                    </div>
                    {audioUrl && (
                      <button 
                        onClick={togglePlay}
                        className="w-12 h-12 rounded-full bg-ghibli-sage text-white flex items-center justify-center shadow-md hover:scale-110 transition-transform"
                      >
                        {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 translate-x-0.5" />}
                      </button>
                    )}
                    {isAudioLoading && <Loader2 className="w-6 h-6 animate-spin text-ghibli-sage" />}
                  </div>
                  
                  <div className="space-y-3 font-sans">
                    {podcastScript.map((turn, i) => (
                      <motion.div 
                        key={i} 
                        initial={{ opacity: 0, x: turn.speaker === '준호' ? -10 : 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.2 }}
                        className={`flex flex-col ${turn.speaker === '준호' ? 'items-start' : 'items-end'}`}
                      >
                        <span className="text-[10px] font-bold text-ghibli-brown/50 mb-1">{turn.speaker}</span>
                        <div className={`px-4 py-2 rounded-2xl max-w-[80%] text-sm ${turn.speaker === '준호' ? 'bg-white text-ghibli-brown rounded-tl-none' : 'bg-ghibli-sage text-white rounded-tr-none'}`}>
                          {turn.text}
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  <audio 
                    ref={audioRef} 
                    src={audioUrl || ''} 
                    onEnded={() => setIsPlaying(false)} 
                    className="hidden" 
                  />
                </motion.div>
              )}

              <div className="flex flex-col lg:flex-row gap-8 items-start">
                <div className="flex-1 space-y-6 w-full">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-5 h-5 text-ghibli-sandy" />
                    <h2 className="text-xl font-serif font-bold">당신을 기다리고 있는 책들</h2>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {recommendations.map((rec, index) => (
                      <motion.div 
                        key={index} 
                        initial={{ opacity: 0, x: -20 }} 
                        animate={{ opacity: 1, x: 0 }} 
                        transition={{ delay: index * 0.1 }} 
                        className="ghibli-card p-5 bg-white/40 border-l-4 border-l-ghibli-sage group relative"
                      >
                        <h3 className="font-serif font-bold text-lg mb-2 text-ghibli-brown">{rec.title}</h3>
                        <p className="text-sm text-ghibli-brown/80 italic mb-4">"{rec.reason}"</p>
                        <button 
                          onClick={() => startChat(rec)}
                          className="flex items-center gap-2 text-xs font-bold text-ghibli-sage hover:text-ghibli-brown transition-colors"
                        >
                          <MessageCircle className="w-4 h-4" />
                          {rec.protagonist}와 대화하기
                        </button>
                      </motion.div>
                    ))}
                  </div>
                </div>

                {generatedCharacterUrl && (
                  <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="w-full lg:w-[300px] shrink-0">
                    <div className="ghibli-card p-4 bg-white/70 shadow-xl">
                      <div className="flex items-center gap-2 mb-3 text-ghibli-brown/80">
                        <User className="w-4 h-4" />
                        <span className="text-xs font-serif font-bold tracking-widest uppercase">My Character</span>
                      </div>
                      <img src={generatedCharacterUrl} alt="Character" referrerPolicy="no-referrer" className="w-full aspect-square object-cover rounded-lg shadow-inner mb-4" />
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Character Chat Window */}
              <AnimatePresence>
                {activeChatBook && (
                  <motion.div 
                    initial={{ opacity: 0, y: 50 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    exit={{ opacity: 0, y: 50 }}
                    className="fixed bottom-24 right-4 md:right-8 w-[calc(100%-2rem)] md:w-80 h-96 bg-white rounded-2xl shadow-2xl border border-ghibli-sandy z-50 flex flex-col pointer-events-auto"
                  >
                    <div className="p-4 border-b border-ghibli-sandy bg-ghibli-beige/30 flex items-center justify-between rounded-t-2xl">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-ghibli-sage flex items-center justify-center text-white">
                          <User className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="text-sm font-bold text-ghibli-brown">{activeChatBook.protagonist}</h4>
                          <p className="text-[10px] text-ghibli-brown/60 truncate w-32">{activeChatBook.title}</p>
                        </div>
                      </div>
                      <button onClick={() => setActiveChatBook(null)} className="p-1 hover:bg-red-50 text-red-500 rounded-full transition-colors">
                        <X className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                      {chatMessages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                          <div className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-ghibli-sage text-white rounded-tr-none' : 'bg-ghibli-beige/40 text-ghibli-brown rounded-tl-none'}`}>
                            {msg.text}
                          </div>
                        </div>
                      ))}
                      {isChatLoading && (
                        <div className="flex justify-start">
                          <div className="bg-ghibli-beige/40 p-2 rounded-2xl">
                            <Loader2 className="w-4 h-4 animate-spin text-ghibli-sage" />
                          </div>
                        </div>
                      )}
                      <div ref={chatEndRef} />
                    </div>

                    <div className="p-3 border-t border-ghibli-sandy bg-white rounded-b-2xl">
                      <div className="flex gap-2">
                        <input 
                          type="text" 
                          value={chatInput}
                          onChange={(e) => setChatInput(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && sendChatMessage()}
                          placeholder="메시지를 입력하세요..."
                          className="flex-1 bg-ghibli-beige/20 border-none focus:ring-1 focus:ring-ghibli-sage rounded-full px-4 py-2 text-sm outline-none"
                        />
                        <button 
                          onClick={sendChatMessage}
                          disabled={isChatLoading || !chatInput.trim()}
                          className="p-2 aspect-square rounded-full bg-ghibli-sage text-white disabled:opacity-50 hover:scale-105 transition-transform"
                        >
                          <Send className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
              
              <div className="flex justify-center mt-12 pb-10">
                <button onClick={() => { setMood(''); setSelectedImage(null); setRecommendations([]); setGeneratedCharacterUrl(null); setPodcastScript([]); setAudioUrl(null); setIsPlaying(false); setActiveChatBook(null); }} className="text-ghibli-brown/60 hover:text-ghibli-brown flex items-center gap-2 text-sm transition-all hover:bg-ghibli-sandy/10 px-4 py-2 rounded-full">
                  <RefreshCcw className="w-4 h-4" /> 다시 하기
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 bg-red-100 border border-red-200 text-red-700 rounded-xl text-center font-sans mt-4">
            {error}
          </motion.div>
        )}
      </main>

      <footer className="fixed bottom-0 left-0 w-full p-4 bg-gradient-to-t from-ghibli-beige to-transparent pointer-events-none z-50">
        <div className="max-w-4xl mx-auto flex flex-col items-center gap-2 text-ghibli-brown/30 text-[10px]">
          <div className="flex gap-4 pointer-events-auto"><span>🌿</span><span>☕</span><span>📜</span></div>
          <p>© 2026 수학교사 사서 선생님의 지브리 도서관</p>
        </div>
      </footer>
    </div>
  );
}

// Helper Upload icon
function Upload(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" x2="12" y1="3" y2="15" />
    </svg>
  );
}

