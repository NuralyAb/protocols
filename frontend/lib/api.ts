import axios from 'axios';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  withCredentials: false,
});

export function setAuthToken(token: string | null) {
  if (token) api.defaults.headers.common.Authorization = `Bearer ${token}`;
  else delete api.defaults.headers.common.Authorization;
}

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && typeof window !== 'undefined') {
      try {
        localStorage.removeItem('protocol-ai-auth');
      } catch {}
    }
    return Promise.reject(err);
  }
);

// ---- Jobs ----
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type TranscriptSegment = {
  speaker: string;
  role?: string | null;
  language?: string | null;
  input_modality?: 'speech' | 'sign';
  start_time: number;
  end_time: number;
  text: string;
  confidence?: number | null;
};

export type Participant = {
  id: string;
  label: string;
  role?: string | null;
};

export type Decision = { text: string; votes?: { for?: number; against?: number; abstain?: number } | null };
export type ActionItem = { task: string; assignee?: string | null; deadline?: string | null };
export type Discussion = { topic: string; summary: string; speakers?: string[] };

export type JobResult = {
  transcript: TranscriptSegment[];
  protocol: {
    title?: string | null;
    date?: string | null;
    participants: Participant[];
    agenda: string[];
    discussion: Discussion[];
    decisions: Decision[];
    action_items: ActionItem[];
  };
  metadata: {
    duration_ms?: number;
    languages_detected?: string[];
    model_versions?: Record<string, string>;
    summarization_error?: string;
  };
};

export type JobBrief = {
  id: string;
  title?: string | null;
  status: JobStatus;
  progress: number;
  source_filename?: string | null;
  duration_ms?: number | null;
  created_at: string;
  updated_at: string;
  result?: JobResult | null;
};

export const jobsApi = {
  list: () => api.get<JobBrief[]>('/api/v1/jobs'),
  upload: (file: File, languages: string, title?: string, onProgress?: (pct: number) => void) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('languages', languages);
    if (title) fd.append('title', title);
    return api.post<{ job_id: string; status: JobStatus }>('/api/v1/build_protocol', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (!onProgress || !e.total) return;
        onProgress(Math.round((e.loaded * 100) / e.total));
      },
    });
  },
  status: (id: string) =>
    api.get<{ id: string; status: JobStatus; progress: number; error?: string | null }>(
      `/api/v1/jobs/${id}`
    ),
  result: (id: string) => api.get<JobBrief>(`/api/v1/jobs/${id}/result`),
  patchSpeakers: (
    id: string,
    patches: Array<{ diarization_id: string; label?: string; role?: string }>
  ) => api.patch(`/api/v1/jobs/${id}/speakers`, patches),
  exportUrl: (id: string, format: 'pdf' | 'docx' | 'json' | 'txt' | 'srt' | 'vtt') =>
    `${api.defaults.baseURL}/api/v1/jobs/${id}/export?format=${format}`,
  audio: (id: string) => api.get<JobAudio>(`/api/v1/jobs/${id}/audio`),
  generateProtocol: (id: string, template_id: string, format: ProtocolFormat) =>
    api.post<Blob>(
      `/api/v1/jobs/${id}/protocol`,
      { template_id, format },
      { responseType: 'blob' }
    ),
  insights: (id: string, opts?: { keyMoments?: boolean }) =>
    api.get<Insights>(`/api/v1/jobs/${id}/insights`, {
      params: { key_moments: opts?.keyMoments ?? true },
    }),
};

export type JobAudio = {
  url: string;
  download_url: string;
  filename: string;
  content_type: string;
  duration_ms?: number | null;
};

export type AsrProvider = 'openai' | 'local' | 'local_kazakh' | 'hf_kazakh';

export type LiveSession = {
  id: string;
  title?: string | null;
  is_active: boolean;
  languages?: string[] | null;
  asr_provider?: AsrProvider;
  audio_key?: string | null;
  started_at: string;
  ended_at?: string | null;
};

export type ProtocolTemplate = {
  id: string;
  name: string;
  description: string;
  language: string;
};

export type ProtocolFormat = 'markdown' | 'docx' | 'pdf';

export type TranslateLang = 'kk' | 'ru' | 'en';

export type ViewerToken = {
  session_id: string;
  viewer_token: string;
  public_url_path: string;
};

export type PublicSession = {
  id: string;
  title?: string | null;
  is_active: boolean;
  languages?: string[] | null;
  started_at: string;
  ended_at?: string | null;
};

export type SpeakerStat = {
  id: string;
  label: string;
  speaking_ms: number;
  segments: number;
  words: number;
  share: number;
};

export type WordStat = { word: string; count: number };

export type KeyMomentKind =
  | 'decision'
  | 'disagreement'
  | 'vote'
  | 'proposal'
  | 'highlight';

export type KeyMoment = {
  at_ms: number;
  speaker: string;
  kind: KeyMomentKind;
  summary: string;
};

export type Insights = {
  speakers: SpeakerStat[];
  top_words: WordStat[];
  key_moments: KeyMoment[];
  totals: {
    speaking_ms: number;
    segments: number;
    speakers: number;
    words: number;
  };
};

export const translateApi = {
  translate: (payload: { text: string; source?: string | null; target: TranslateLang }) =>
    api.post<{ text: string; source: string | null; target: string }>(
      '/api/v1/translate',
      payload,
    ),
};

export const sessionsApi = {
  list: () => api.get<LiveSession[]>('/api/v1/sessions'),
  create: (payload: { title?: string; languages?: string[]; asr_provider?: AsrProvider }) =>
    api.post<LiveSession>('/api/v1/sessions', payload),
  get: (id: string) => api.get<LiveSession>(`/api/v1/sessions/${id}`),
  audio: (id: string) =>
    api.get<{ url: string; download_url: string; filename: string; content_type: string }>(
      `/api/v1/sessions/${id}/audio`
    ),
  snapshot: (id: string) => api.get<JobResult>(`/api/v1/sessions/${id}/snapshot`),
  exportUrl: (id: string, format: 'pdf' | 'docx' | 'json' | 'txt' | 'srt' | 'vtt') =>
    `${api.defaults.baseURL}/api/v1/sessions/${id}/export?format=${format}`,
  patchSpeakers: (
    id: string,
    patches: Array<{ diarization_id: string; label?: string; role?: string }>
  ) => api.patch(`/api/v1/sessions/${id}/speakers`, patches),
  listTemplates: () => api.get<ProtocolTemplate[]>('/api/v1/sessions/templates'),
  uploadTemplate: (payload: {
    name: string;
    description?: string;
    language?: string;
    file?: File;
    body?: string;
  }) => {
    const fd = new FormData();
    fd.append('name', payload.name);
    if (payload.description) fd.append('description', payload.description);
    if (payload.language) fd.append('language', payload.language);
    if (payload.file) fd.append('file', payload.file);
    if (payload.body) fd.append('body', payload.body);
    return api.post<ProtocolTemplate>('/api/v1/sessions/templates', fd);
  },
  generateProtocol: (id: string, template_id: string, format: ProtocolFormat) =>
    api.post<Blob>(
      `/api/v1/sessions/${id}/protocol`,
      { template_id, format },
      { responseType: 'blob' }
    ),
  insights: (id: string, opts?: { keyMoments?: boolean }) =>
    api.get<Insights>(`/api/v1/sessions/${id}/insights`, {
      params: { key_moments: opts?.keyMoments ?? true },
    }),
  mintViewerToken: (id: string, opts?: { rotate?: boolean }) =>
    api.post<ViewerToken>(
      `/api/v1/sessions/${id}/viewer_token`,
      undefined,
      { params: { rotate: opts?.rotate ?? false } },
    ),
  publicMeta: (id: string, token: string) =>
    api.get<PublicSession>(`/api/v1/sessions/${id}/public`, { params: { token } }),
  publicTranscript: (id: string, token: string) =>
    api.get<JobResult>(`/api/v1/sessions/${id}/public/transcript`, { params: { token } }),
};
