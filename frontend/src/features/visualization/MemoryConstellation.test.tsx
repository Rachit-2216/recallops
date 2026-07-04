import { fireEvent, render, screen } from "@testing-library/react";

import { MemoryConstellation } from "./MemoryConstellation";
import { CONSTELLATION_NODES } from "./constellationData";
import {
  selectConstellationMode,
  selectFrameLoop,
  selectSceneStatus,
} from "./constellationPolicy";

it("uses a static scene when motion or platform capability requires it", () => {
  expect(
    selectConstellationMode({
      compactViewport: false,
      reducedMotion: true,
      webglAvailable: true,
    }),
  ).toBe("fallback");
  expect(
    selectConstellationMode({
      compactViewport: true,
      reducedMotion: false,
      webglAvailable: true,
    }),
  ).toBe("fallback");
  expect(
    selectConstellationMode({
      compactViewport: false,
      reducedMotion: false,
      webglAvailable: true,
    }),
  ).toBe("webgl");
});

it("pauses continuous rendering when the scene is hidden or offscreen", () => {
  expect(selectFrameLoop({ documentVisible: true, inViewport: true })).toBe(
    "always",
  );
  expect(selectFrameLoop({ documentVisible: false, inViewport: true })).toBe(
    "demand",
  );
  expect(selectFrameLoop({ documentVisible: true, inViewport: false })).toBe(
    "demand",
  );
});

it("reports WebGL as active only after the first rendered frame", () => {
  expect(selectSceneStatus("webgl", false)).toBe("3D WARMING");
  expect(selectSceneStatus("webgl", true)).toBe("3D ACTIVE");
  expect(selectSceneStatus("fallback", false)).toBe("STATIC SAFE MODE");
});

it("maps the case-study evidence into accessible scene controls", () => {
  render(<MemoryConstellation />);

  expect(
    screen.getByRole("img", { name: /static incident memory constellation/i }),
  ).toBeVisible();
  expect(
    screen.getAllByRole("button", { name: /inspect evidence node/i }),
  ).toHaveLength(CONSTELLATION_NODES.length);

  fireEvent.click(
    screen.getByRole("button", {
      name: /inspect evidence node: november 18 outage/i,
    }),
  );
  expect(screen.getByText(/shared global propagation risk/i)).toBeVisible();
});
