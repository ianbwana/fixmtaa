/**
* PASS TWO ADDITIONAL OPTIONS IN THIS ORDER:
* twitter_handle, filename[end name with .json]
*/


var TwitterPosts, streamOfTweets;
TwitterPosts = require('twitter-screen-scrape');

var fs = require('fs');
var path = require('path');

streamOfTweets = new TwitterPosts({
  username: process.argv[2],
  retweets: false
});

store_tweets = [];

streamOfTweets.on('readable', function() {
  var time, tweet;
  tweet = streamOfTweets.read();
  time = new Date(tweet.time * 1000);
  console.log(tweet);
  /*
  console.log([
    "KenyaPower_Care's tweet from ",
    time.toLocaleDateString(),
    " got ",
    tweet.favorite,
    " favorites, ",
    tweet.reply,
    " replies, and ",
    tweet.retweet,
    " retweets"
  ].join(''));
  */

  store_tweets.push({
    'tweet': tweet.text,
    'time': time.toLocaleDateString()
  });

});



function storeTweets(){

  var file = path.join(__dirname, 'output', process.argv[3]);

  fs.writeFileSync(file,JSON.stringify(store_tweets));

}

streamOfTweets.on('end', function(){

  console.log('stream of tweets ended');
  storeTweets();

});

streamOfTweets.on('close', function(){

  console.log('stream of tweets closed');
  storeTweets();

});

process.on('SIGINT', function() {
    console.log("Caught interrupt signal");
    storeTweets();
    process.exit();
});
