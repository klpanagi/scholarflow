import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className || ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            return match ? (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                className="rounded-lg text-xs my-3"
              >
                {String(children).replace(/\n$/, "")}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          table({ children, ...props }) {
            return (
              <div className="overflow-x-auto my-3">
                <table className="min-w-full divide-y divide-border" {...props}>
                  {children}
                </table>
              </div>
            );
          },
          thead({ children, ...props }) {
            return <thead className="bg-muted/50" {...props}>{children}</thead>;
          },
          th({ children, ...props }) {
            return (
              <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider" {...props}>
                {children}
              </th>
            );
          },
          td({ children, ...props }) {
            return (
              <td className="px-3 py-2 text-sm border-t border-border" {...props}>
                {children}
              </td>
            );
          },
          h1({ children, ...props }) {
            return <h1 className="text-xl font-bold mt-6 mb-3 text-foreground" {...props}>{children}</h1>;
          },
          h2({ children, ...props }) {
            return <h2 className="text-lg font-semibold mt-5 mb-2 text-foreground" {...props}>{children}</h2>;
          },
          h3({ children, ...props }) {
            return <h3 className="text-base font-semibold mt-4 mb-2 text-foreground" {...props}>{children}</h3>;
          },
          ul({ children, ...props }) {
            return <ul className="list-disc list-inside space-y-1 my-2" {...props}>{children}</ul>;
          },
          ol({ children, ...props }) {
            return <ol className="list-decimal list-inside space-y-1 my-2" {...props}>{children}</ol>;
          },
          li({ children, ...props }) {
            return <li className="text-sm" {...props}>{children}</li>;
          },
          blockquote({ children, ...props }) {
            return (
              <blockquote className="border-l-4 border-primary/30 pl-4 my-3 italic text-muted-foreground" {...props}>
                {children}
              </blockquote>
            );
          },
          a({ children, href, ...props }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80" {...props}>
                {children}
              </a>
            );
          },
          hr(props) {
            return <hr className="my-6 border-border" {...props} />;
          },
          strong({ children, ...props }) {
            return <strong className="font-semibold text-foreground" {...props}>{children}</strong>;
          },
          p({ children, ...props }) {
            return <p className="text-sm leading-relaxed my-2" {...props}>{children}</p>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
