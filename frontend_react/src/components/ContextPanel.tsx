interface Props {
  anchors: { id: string; text: string }[]
}

export default function ContextPanel({ anchors }: Props) {
  if (!anchors.length) return null
  return (
    <>
      <style>{`
        html { scroll-behavior: smooth; }
        .ctx-panel {
          position: fixed; right: 0; top: 50%; transform: translateY(-50%);
          width: 8px; max-height: 60vh;
          background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
          border-radius: 4px 0 0 4px;
          transition: width 0.25s, padding 0.25s, box-shadow 0.25s;
          overflow: hidden; z-index: 9999; cursor: pointer;
        }
        .ctx-panel:hover {
          width: 220px; padding: 10px 12px;
          background: #fff; box-shadow: -4px 0 20px rgba(0,0,0,0.12);
          border: 1px solid #e8e8e8; border-right: none; overflow-y: auto;
        }
        .ctx-item {
          display: block; padding: 7px 10px; font-size: 13px;
          color: #333 !important; text-decoration: none !important;
          border-radius: 6px; white-space: nowrap; overflow: hidden;
          text-overflow: ellipsis; transition: background 0.15s;
        }
        .ctx-item:hover { background: #f0f2ff; }
      `}</style>
      <div className="ctx-panel">
        {anchors.map((a) => (
          <a key={a.id} className="ctx-item" href={`#${a.id}`} title={a.text}>
            {a.text}
          </a>
        ))}
      </div>
    </>
  )
}
