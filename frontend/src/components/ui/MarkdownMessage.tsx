import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/cn';

export function MarkdownMessage({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn('max-w-none text-[13px] leading-relaxed text-ink-800', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="mb-2 text-[15px] font-semibold text-ink-900">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 text-[14px] font-semibold text-ink-900">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 text-[13px] font-semibold text-ink-900">{children}</h3>,
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-ink-900">{children}</strong>,
          ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          code: ({ children }) => (
            <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[12px] text-ink-800">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="mb-2 overflow-x-auto rounded-lg bg-ink-900 p-3 text-[12px] text-white">
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div className="my-2 max-w-full overflow-x-auto rounded-lg border border-line bg-white">
              <table className="min-w-full border-collapse text-left text-[12px]">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-slate-50 text-ink-700">{children}</thead>,
          th: ({ children }) => <th className="border-b border-line px-3 py-2 font-semibold">{children}</th>,
          td: ({ children }) => <td className="border-b border-line px-3 py-2 align-top last:border-b-0">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
