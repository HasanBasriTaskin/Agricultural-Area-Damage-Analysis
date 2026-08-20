/**
 * polygonUtils.ts
 * 
 * Harita poligon çizimlerinde en yakın kenara köşe ekleme,
 * kesişim önleme ve küresel alan hesabı araçları.
 */

const EARTH_RADIUS_METERS = 6371008.8;
const DEG_TO_RAD = Math.PI / 180;

export type LatLngTuple = [number, number]; // [lat, lng]

export function getDistanceMeters(p1: LatLngTuple, p2: LatLngTuple): number {
  const dLat = (p2[0] - p1[0]) * DEG_TO_RAD;
  const dLng = (p2[1] - p1[1]) * DEG_TO_RAD;
  const avgLat = ((p1[0] + p2[0]) / 2) * DEG_TO_RAD;

  const x = dLng * Math.cos(avgLat);
  const y = dLat;

  return Math.sqrt(x * x + y * y) * EARTH_RADIUS_METERS;
}

function ccw(p1: LatLngTuple, p2: LatLngTuple, p3: LatLngTuple): boolean {
  return (p3[0] - p1[0]) * (p2[1] - p1[1]) > (p2[0] - p1[0]) * (p3[1] - p1[1]);
}

export function doSegmentsIntersect(
  p1: LatLngTuple,
  p2: LatLngTuple,
  p3: LatLngTuple,
  p4: LatLngTuple
): boolean {
  if (
    (p1[0] === p3[0] && p1[1] === p3[1]) ||
    (p1[0] === p4[0] && p1[1] === p4[1]) ||
    (p2[0] === p3[0] && p2[1] === p3[1]) ||
    (p2[0] === p4[0] && p2[1] === p4[1])
  ) {
    return false;
  }

  return (
    ccw(p1, p3, p4) !== ccw(p2, p3, p4) &&
    ccw(p1, p2, p3) !== ccw(p1, p2, p4)
  );
}

export function isPolygonSelfIntersecting(points: LatLngTuple[]): boolean {
  if (!points || points.length < 4) return false;
  const n = points.length;

  for (let i = 0; i < n; i++) {
    const a1 = points[i];
    const a2 = points[(i + 1) % n];

    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue;
      const b1 = points[j];
      const b2 = points[(j + 1) % n];

      if (doSegmentsIntersect(a1, a2, b1, b2)) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Yeni noktayı poligonun en yakın kenarının arasına yerleştirir.
 */
export function insertPointIntoPolygon(
  points: LatLngTuple[],
  newPoint: LatLngTuple,
  avoidIntersection = true
): LatLngTuple[] {
  if (!points || points.length === 0) {
    return [newPoint];
  }

  if (points.length < 3) {
    return [...points, newPoint];
  }

  const n = points.length;
  const candidates: {
    edgeIndex: number;
    increase: number;
    candidateList: LatLngTuple[];
    causesIntersection: boolean;
  }[] = [];

  for (let i = 0; i < n; i++) {
    const pA = points[i];
    const pB = points[(i + 1) % n];

    const currentEdgeLen = getDistanceMeters(pA, pB);
    const lenToNew = getDistanceMeters(pA, newPoint) + getDistanceMeters(newPoint, pB);
    const increase = lenToNew - currentEdgeLen;

    const candidateList: LatLngTuple[] = [...points];
    candidateList.splice(i + 1, 0, newPoint);

    const causesIntersection = avoidIntersection ? isPolygonSelfIntersecting(candidateList) : false;

    candidates.push({
      edgeIndex: i,
      increase,
      candidateList,
      causesIntersection,
    });
  }

  if (avoidIntersection) {
    const nonIntersecting = candidates.filter((c) => !c.causesIntersection);
    if (nonIntersecting.length > 0) {
      nonIntersecting.sort((a, b) => a.increase - b.increase);
      return nonIntersecting[0].candidateList;
    }
  }

  candidates.sort((a, b) => a.increase - b.increase);
  return candidates[0].candidateList;
}