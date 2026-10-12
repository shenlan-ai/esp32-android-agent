export function screenPoint(clientX, clientY, rect, imageWidth, imageHeight) {
  if (!imageWidth || !imageHeight || !rect.width || !rect.height) return null;
  const ratio = imageWidth / imageHeight;
  const width = Math.min(rect.width, rect.height * ratio), height = width / ratio;
  const x = (clientX - rect.left - (rect.width - width) / 2) / width;
  const y = (clientY - rect.top - (rect.height - height) / 2) / height;
  if (x < 0 || x > 1 || y < 0 || y > 1) return null;
  return { x: Math.round(x * 1000), y: Math.round(y * 1000) };
}
