type ConstellationCapability = {
  compactViewport: boolean;
  reducedMotion: boolean;
  webglAvailable: boolean;
};

export function selectConstellationMode({
  compactViewport,
  reducedMotion,
  webglAvailable,
}: ConstellationCapability): "fallback" | "webgl" {
  return compactViewport || reducedMotion || !webglAvailable
    ? "fallback"
    : "webgl";
}

export function selectFrameLoop({
  documentVisible,
  inViewport,
}: {
  documentVisible: boolean;
  inViewport: boolean;
}): "always" | "demand" {
  return documentVisible && inViewport ? "always" : "demand";
}

export function selectSceneStatus(
  mode: "fallback" | "webgl",
  sceneReady: boolean,
) {
  if (mode === "fallback") return "STATIC SAFE MODE";
  return sceneReady ? "3D ACTIVE" : "3D WARMING";
}
