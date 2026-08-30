// Pure display/sorting helpers. Contains NO AI/ML logic — relationship
// scores are expected to come from the backend/ML team via searchService.
// This file only interprets and sorts the numbers it's given.

export function getRelationshipStrength(score) {
  if (score >= 90) return 'Very High'
  if (score >= 70) return 'High'
  if (score >= 40) return 'Medium'
  return 'Low'
}

export const strengthColors = {
  'Very High': 'bg-danger/10 text-danger',
  High: 'bg-warning/10 text-warning',
  Medium: 'bg-primary/10 text-primary',
  Low: 'bg-text-secondary/10 text-text-secondary',
}

// Sorts relationships by relationshipScore, highest first.
export function sortByRelationshipScore(relationships = []) {
  return [...relationships].sort((a, b) => b.relationshipScore - a.relationshipScore)
}