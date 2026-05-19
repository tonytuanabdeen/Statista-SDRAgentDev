List<Lead> leads = new List<Lead>();

Lead l = new Lead(
    FirstName= 'TestLead',
    LastName= 'TestingCenter-001',
    Title= 'Chief Marketing Officer',
    Industry= 'MANUFACTURING',
    Company= 'Journeyhorizon',
    Country= 'United Kingdom',
    LeadRole__c= 'Coach',
    ProductOfInterest__c= 'BASIC_ACCOUNT_PLUS',
    SubscriptionStatus__c= 'non-subscriber',
    Website= 'https://www.journeyh.io',
    Email= 'TestLead@TestingCenter001.io',
    LeadSource= 'Webform',
    Status= 'MQL');
leads.add(l);

l = new Lead(
    FirstName= 'TestLead',
    LastName= 'TestingCenter-002',
    Title= 'Head of Data Engineering',
    Industry= 'MANUFACTURING',
    Company= 'Journeyhorizon',
    Country= 'United Kingdom',
    LeadRole__c= 'Coach',
    ProductOfInterest__c= 'BASIC_ACCOUNT_PLUS',
    SubscriptionStatus__c= 'non-subscriber',
    Website= 'https://www.journeyh.io',
    Email= 'TestLead@TestingCenter002.io',
    LeadSource= 'Webform',
    Status= 'MQL');
leads.add(l);

l = new Lead(
    FirstName= 'TestLead',
    LastName= 'TestingCenter-003',
    Title= 'VP of Strategy',
    Industry= 'MANUFACTURING',
    Company= 'Journeyhorizon',
    Country= 'United Kingdom',
    LeadRole__c= 'Coach',
    ProductOfInterest__c= 'BASIC_ACCOUNT_PLUS',
    SubscriptionStatus__c= 'non-subscriber',
    Website= 'https://www.journeyh.io',
    Email= 'TestLead@TestingCenter003.io',
    LeadSource= 'Webform',
    Status= 'MQL');
leads.add(l);

insert leads;