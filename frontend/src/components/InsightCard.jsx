function InsightCard({ insight }) {
  return (
    <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-6 rounded-2xl shadow-lg">

      <h2 className="text-2xl font-bold mb-3">
        AI Insight
      </h2>

      <p className="text-lg leading-relaxed">
        {insight}
      </p>

    </div>
  );
}

export default InsightCard;