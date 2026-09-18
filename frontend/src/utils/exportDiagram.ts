import { toPng } from "html-to-image";
import { jsPDF } from "jspdf";

// Captures the React Flow viewport element (nodes + edges, at their real pre-transform layout
// size) rather than the outer pane - this naturally excludes the on-screen Controls buttons and
// the "React Flow" attribution badge, which live outside the viewport element, giving a clean
// diagram image suitable for documentation.
async function captureViewportPng(containerEl: HTMLElement): Promise<string> {
  const viewport = containerEl.querySelector<HTMLElement>(".react-flow__viewport");
  if (!viewport) throw new Error("Could not find the diagram canvas to export");

  // html-to-image's style-inlining misses `fill` when it comes from a stylesheet rule on an SVG
  // element (rather than an inline style/attribute) - the edge label's background <rect> is
  // styled that way, so it rasterizes as SVG's black default fill instead of the real (usually
  // white) color. Pin down the real computed fill as an inline style just for the capture, then
  // restore it, rather than leaving a black box behind the connection label in every export.
  const labelBackgrounds = Array.from(viewport.querySelectorAll<SVGRectElement>(".react-flow__edge-textbg"));
  const originalFills = labelBackgrounds.map((el) => el.style.fill);
  labelBackgrounds.forEach((el) => {
    el.style.fill = getComputedStyle(el).fill;
  });
  try {
    return await toPng(viewport, { backgroundColor: "#ffffff", pixelRatio: 2 });
  } finally {
    labelBackgrounds.forEach((el, i) => {
      el.style.fill = originalFills[i];
    });
  }
}

function triggerDownload(dataUrl: string, filename: string) {
  const link = document.createElement("a");
  link.download = filename;
  link.href = dataUrl;
  link.click();
}

export async function downloadDiagramPng(containerEl: HTMLElement, baseName: string) {
  const dataUrl = await captureViewportPng(containerEl);
  triggerDownload(dataUrl, `${baseName}.png`);
}

export async function downloadDiagramPdf(containerEl: HTMLElement, baseName: string) {
  const dataUrl = await captureViewportPng(containerEl);
  const image = new Image();
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error("Could not load the captured diagram image"));
    image.src = dataUrl;
  });
  const orientation = image.width >= image.height ? "landscape" : "portrait";
  const pdf = new jsPDF({ orientation, unit: "pt", format: [image.width, image.height] });
  pdf.addImage(dataUrl, "PNG", 0, 0, image.width, image.height);
  pdf.save(`${baseName}.pdf`);
}
