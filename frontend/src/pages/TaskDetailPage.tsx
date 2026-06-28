import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { apiClient, type TaskRecord } from "@/lib/api";
import { AgentBadge, StatusBadge } from "@/components/StatusBadge";
import { format } from "date-fns";

const easing: [number, number, number, number] = [0.25, 0.46, 0.45, 0.94];

interface SourceInfo {
  url: string;
  type: string;
  title: string;
  chunks_stored: number;
}

interface HitInfo {
  url: string;
  chunk_index: number;
  similarity: number;
}

interface AttachedImage {
  filename: string;
  media_type: string;
  storage_key: string;
}

interface AttachedTextDoc {
  filename: string;
  storage_key: string;
  inline: boolean;
}

export function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const taskId = id!;

  const task = useQuery<TaskRecord>({
    queryKey: ["task", taskId],
    queryFn: async () => {
      try {
        return await apiClient.getTask(taskId);
      } catch {
        try {
          return await apiClient.getResearch(taskId);
        } catch {
          return await apiClient.getPlan(taskId);
        }
      }
    },
    refetchInterval: (q) => {
      const data = q.state.data as TaskRecord | undefined;
      return data?.status === "running" || data?.status === "pending" ? 2_500 : false;
    },
  });

  if (task.isLoading) {
    return <div className="text-center py-20 text-[var(--color-text-muted)]">Loading…</div>;
  }
  if (!task.data) {
    return <div className="text-center py-20 text-rose-400">Task not found</div>;
  }

  const data = task.data;
  const params = (data.params ?? {}) as Record<string, unknown>;
  const sources = (params.sources ?? []) as SourceInfo[];
  const hits = (params.hits_used ?? []) as HitInfo[];
  const attachedImages = (params.attached_images ?? []) as AttachedImage[];
  const attachedTextDocs = (params.attached_text_docs ?? []) as AttachedTextDoc[];
  const planType = params.plan_type as string | undefined;
  const isRunning = data.status === "running" || data.status === "pending";

  return (
    <div className="space-y-8">
      <Link
        to="/tasks"
        className="inline-flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-white transition-colors"
      >
        ← Back to tasks
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: easing }}
        className="space-y-4"
      >
        <div className="flex items-center flex-wrap gap-2">
          <StatusBadge status={data.status} />
          {data.agent && <AgentBadge agent={data.agent} />}
          {planType && (
            <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-text-muted)]">
              · {planType}
            </span>
          )}
          <span className="ml-auto text-xs text-[var(--color-text-muted)] font-mono">
            {format(new Date(data.created_at), "MMM d, yyyy · HH:mm")}
          </span>
        </div>
        <h1 className="font-display text-3xl font-bold leading-tight">{data.prompt}</h1>
      </motion.div>

      {attachedImages.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.08, ease: easing }}
          className="glass rounded-xl p-5"
        >
          <div className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
            Attached images ({attachedImages.length})
          </div>
          <div className="grid grid-cols-3 gap-3">
            {attachedImages.map((img) => (
              <a
                key={img.storage_key}
                href={apiClient.uploadUrl(taskId, img.filename)}
                target="_blank"
                rel="noreferrer"
                className="group block glass rounded-lg overflow-hidden hover:scale-[1.02] transition-transform duration-300 ease-[cubic-bezier(0.25,0.46,0.45,0.94)]"
              >
                <div className="aspect-video bg-black/40 overflow-hidden">
                  <img
                    src={apiClient.uploadUrl(taskId, img.filename)}
                    alt={img.filename}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="px-3 py-2 text-xs">
                  <div className="truncate font-mono">{img.filename}</div>
                  <div className="text-[var(--color-text-muted)] mt-0.5">{img.media_type}</div>
                </div>
              </a>
            ))}
          </div>
        </motion.div>
      )}

      {attachedTextDocs.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.09, ease: easing }}
          className="glass rounded-xl p-5"
        >
          <div className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
            Attached docs ({attachedTextDocs.length})
          </div>
          <ul className="space-y-2 text-sm">
            {attachedTextDocs.map((doc) => (
              <li key={doc.storage_key} className="flex items-center justify-between gap-2">
                <a
                  href={apiClient.uploadUrl(taskId, doc.filename)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--color-accent-cyan)] hover:underline truncate"
                >
                  📄 {doc.filename}
                </a>
                <span className="text-xs font-mono text-[var(--color-text-muted)] whitespace-nowrap">
                  {doc.inline ? "inline (<8KB)" : "via RAG"}
                </span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {sources.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1, ease: easing }}
          className="glass rounded-xl p-5"
        >
          <div className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
            Sources ({sources.length})
          </div>
          <ul className="space-y-2">
            {sources.map((s) => (
              <li key={s.url} className="flex items-center justify-between gap-3 text-sm">
                <a
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-[var(--color-accent-cyan)] hover:underline truncate"
                >
                  {s.title || s.url}
                </a>
                <span className="text-xs font-mono text-[var(--color-text-muted)] whitespace-nowrap">
                  {s.chunks_stored} chunks · {s.type}
                </span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {isRunning && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="glass rounded-xl p-8 text-center"
        >
          <div className="inline-flex items-center gap-3 text-[var(--color-text-secondary)]">
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse [animation-delay:200ms]" />
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse [animation-delay:400ms]" />
            <span className="ml-2 text-sm">İşleniyor… polling 2.5sn</span>
          </div>
        </motion.div>
      )}

      {data.error && (
        <div className="glass rounded-xl p-5 border border-rose-500/40 bg-rose-500/10">
          <div className="text-xs uppercase tracking-wider text-rose-300 mb-2">Error</div>
          <pre className="text-sm text-rose-200 whitespace-pre-wrap font-mono">{data.error}</pre>
        </div>
      )}

      {data.result_text && (
        <motion.article
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: easing }}
          className="glass-strong rounded-xl p-8"
        >
          <div className="prose-dark max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {data.result_text}
            </ReactMarkdown>
          </div>
        </motion.article>
      )}

      {data.usage && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: easing }}
          className="glass rounded-xl p-5"
        >
          <div className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-3">Usage</div>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <div className="text-[var(--color-text-muted)] text-xs">Input tokens</div>
              <div className="font-mono font-semibold mt-1">{data.usage.input_tokens.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[var(--color-text-muted)] text-xs">Output tokens</div>
              <div className="font-mono font-semibold mt-1">{data.usage.output_tokens.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[var(--color-text-muted)] text-xs">Cache read</div>
              <div className="font-mono font-semibold mt-1">{data.usage.cache_read_tokens.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[var(--color-text-muted)] text-xs">Cost</div>
              <div className="font-mono font-semibold mt-1 text-[var(--color-accent-cyan)]">
                ${data.usage.cost_usd.toFixed(4)}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {hits.length > 0 && (
        <details className="glass rounded-xl p-5">
          <summary className="cursor-pointer text-xs uppercase tracking-wider text-[var(--color-text-muted)]">
            RAG hits used ({hits.length})
          </summary>
          <ul className="mt-3 space-y-1 text-xs font-mono">
            {hits.map((h, i) => (
              <li key={i} className="flex items-center justify-between gap-3">
                <span className="text-[var(--color-text-muted)] truncate">
                  #{h.chunk_index} {h.url}
                </span>
                <span className="text-[var(--color-accent-cyan)] whitespace-nowrap">
                  sim {h.similarity.toFixed(3)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
