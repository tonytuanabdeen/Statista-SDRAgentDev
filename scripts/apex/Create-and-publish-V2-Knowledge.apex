// 1. Create the new Knowledge Article with Data Category selection
// use this command before sf data treet import to create the knowledge artciles. Copy and paste the script to the terminal window
/*
sf data tree import -f scripts/data/V2-Knowledge__kav-Knowledge__DataCategorySelection.json
*/

// 2. Publish the Knowledge Article
// Execute the following code using the Execute Anonymous Apex feature
List<Knowledge__kav> kavs = [SELECT KnowledgeArticleId FROM Knowledge__kav WHERE Title LIKE 'LNA%' AND PublishStatus = 'Draft'];
for ( Knowledge__kav k : kavs ) {
	KbManagement.PublishingService.publishArticle(k.KnowledgeArticleId, true);
}