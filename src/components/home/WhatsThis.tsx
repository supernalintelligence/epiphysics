const cards = [
  {
    title: 'A Research Question',
    body: 'Which representations help us predict changing systems? Epimechanics proposes mathematical candidates; Epiphysics compares them against evidence.',
  },
  {
    title: 'Assumptions Made Visible',
    body: 'Definitions, structural postulates, conditional results, and empirical claims need different evidence. Each claim should retain its assumptions and limits.',
  },
  {
    title: 'Human + AI',
    body: 'Human researchers and AI collaborators propose, implement, and critique ideas. Reviewable records and independent tests determine what can be claimed.',
  },
];

const goals = [
  { label: 'Foundation', text: 'Preserve evidence and prospective prediction records' },
  { label: 'Evaluation', text: 'Compare representations on new outcomes at declared cost' },
  { label: 'Long-term', text: 'Test transfer between environments and document where it fails' },
];

export default function WhatsThis() {
  return (
    <section className="w-full bg-white dark:bg-gray-950 py-14 sm:py-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* What is this */}
        <div className="text-center max-w-3xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-900 dark:text-white">What is this?</h2>
          <p className="mt-3 text-base sm:text-lg text-gray-600 dark:text-gray-300">
            An open research program for representations, recursive systems, and testable predictions.
          </p>
        </div>

        <div className="mt-8 sm:mt-10 grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
          {cards.map((card) => (
            <article
              key={card.title}
              className="rounded-2xl border border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900/70 p-5 sm:p-6"
            >
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-white">{card.title}</h3>
              <p className="mt-3 text-sm sm:text-base leading-relaxed text-gray-700 dark:text-gray-300">{card.body}</p>
            </article>
          ))}
        </div>

        {/* Goals timeline */}
        <div className="mt-16 max-w-3xl mx-auto">
          <h3 className="text-xl sm:text-2xl font-bold text-center text-gray-900 dark:text-white mb-8">Roadmap</h3>
          <div className="space-y-4">
            {goals.map((goal, i) => (
              <div key={i} className="flex items-start gap-4">
                <span className="flex-shrink-0 w-24 text-sm font-semibold text-blue-600 dark:text-blue-400">{goal.label}</span>
                <span className="text-gray-700 dark:text-gray-300">{goal.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
