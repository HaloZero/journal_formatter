# Journal Analyzer

I've been keeping a daily journal for a few years now and decided to open source some of the analysis I've been doing on the records as well as keeping a easier to see format of the records. I don't think anything here has been super insightful but it's fun to look over the data and see if there are any patterns. It was also a fun way to explore and mess with NLTK and play around.

## Main Features

The system has some simple features including a nice way to look at past months of data and a simple search feature.

[example entry]()

### Day in History

Instead of searching for entries at a specific date you can see the history of entires on that date. So if you want to see how you've been spending the past new years you can check out special dates. Or you can just see what you were doing this day a few years ago.

### N-Grams

The N-Grams feature is basically the most common word combinations in a range. By default it looks at ALL your entries but you can narrow it down to a certain range. I think this feature was the most cringe because you realize what silly little tropes. One of my most popular is 100% "I guess we'll see". Which is my I don't know how to end this entry or sentence thought.

### Sentiment Analysis

There's some sentiment analysis by default that uses the NLTK parser to analyze things. But a goal in the future is to allow you to build your own classifier based on your own assessment and then change the system to use that new classifier.

## Setting up your own system

Depending on how you keep the format of your journal you'll need to do a few things.

### JSON

If your journal can be exported to JSON this is the easiest solution. Just create a file in `static/diary-download.json` and then implement your own class that implements the protocol `JournalRecord` in `importer.py`. You can see an example of this with `DailyDiaryJournalEntry`.

### CSV

Effectively you'll need to build your own parser and just make each record conform to `JournalRecord` and just modify `import_entries` in `routes.py` to take the new format in. I'm looking to improve this so it's easier to modify but will work on that in the future

## Starting the app

1) Run Migrations. `flask db upgrade`
2) Start the app server `flask run`
3) In a web browser go to `/import` to start importing your records.
4) Optional: In a web browser go to `/analyze` to analyze and fill in some additional information on your journal entries

You should be able to then see records on your localhost!

## Creating your own sentiment model

The default classifier model is the model provided by NLTK that was trained from various movie reviews. This isn't exactly precise on journal entries but it should work.

If you want to create your own sentiment model, then you can train your own data by going to: `/classify_sentences` and classifying your sentences as positive, negative or neutral. The neutral records are effectively ignored when analyzing your sentiment and it's important to get sufficient records.

You can test the accuracy of your model by running `Classifier.test_local_classifier()` in a flask console (run `flask shell`).

If you're ready to use it, just modify `use_internal_classifier` in `main.js` to true. This is currently only used for local sentence analysis and not the graphs.

## Things to do

- Fixing background threading for `/analyze` and `/import`
- Using parser for other date parsers
- Expand models https://towardsdatascience.com/basic-binary-sentiment-analysis-using-nltk-c94ba17ae386
- Improve how `use_internal_classifier` is used instead of modifying js file. Expand use to other sentiment graphs.
- Prettier Graphs and colors.
- Add tests for request parsers SQL requirements