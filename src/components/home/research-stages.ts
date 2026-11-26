export const researchStages = [
  { id: 'observe', label: 'Observe', title: 'Record the available evidence.', description: 'Save sources as they arrive, including revisions and the time each version was collected.' },
  { id: 'represent', label: 'Represent', title: 'Compare different descriptions.', description: 'Propose entities and relationships at different scales. Treat each representation as a hypothesis to test.' },
  { id: 'predict', label: 'Predict', title: 'Register a prediction.', description: 'Record a probability, deadline, and resolution rule before the outcome is observed.' },
  { id: 'evaluate', label: 'Evaluate', title: 'Compare predictions with outcomes.', description: 'Give methods the same questions and evidence. Account for failures, uncertainty, and cost alongside accuracy.' },
  { id: 'revise', label: 'Revise', title: 'Test the next representation.', description: 'Use completed experiments to propose changes, then evaluate those changes on new observations.' },
] as const;
