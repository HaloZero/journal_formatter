from pychartjs import BaseChart, ChartType, Color, Options

class JournalBaseChart(BaseChart):
	class options:
		legend = Options.Legend(display=False)

	class data:
		backgroundColor = Color.RGBA(211, 200, 217, 1)

class NGramChart(JournalBaseChart):
	type = ChartType.Bar

class NGramChart(JournalBaseChart):
	type = ChartType.Bar

