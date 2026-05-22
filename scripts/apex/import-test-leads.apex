List<Lead> leads = new List<Lead>();

Lead l = new Lead(
    FirstName= 'TestLead',
    LastName= 'TestingCenter-101',
    Title= 'Chief Marketing Officer',
    Industry= 'MANUFACTURING',
    Company= 'Journeyhorizon',
    Country= 'United Kingdom',
    LeadRole__c= 'Coach',
    ProductOfInterest__c= 'BASIC_ACCOUNT_PLUS',
    SubscriptionStatus__c= 'non-subscriber',
    Website= 'https://www.journeyh.io',
    Email= 'tabdeen.dxb@gmail.com',
    LeadSource= 'Webform',
    Status= 'MQL');
leads.add(l);

l = new Lead(
    FirstName= 'TestLead',
    LastName= 'TestingCenter-102',
    Title= 'Head of Data Engineering',
    Industry= 'MANUFACTURING',
    Company= 'Journeyhorizon',
    Country= 'United Kingdom',
    LeadRole__c= 'Coach',
    ProductOfInterest__c= 'BASIC_ACCOUNT_PLUS',
    SubscriptionStatus__c= 'non-subscriber',
    Website= 'https://www.journeyh.io',
    Email= 'tabdeen.dxb@gmail.com',
    LeadSource= 'Webform',
    Status= 'MQL');
leads.add(l);

l = new Lead(
    FirstName= 'TestLead',
    LastName= 'TestingCenter-103',
    Title= 'VP of Strategy',
    Industry= 'MANUFACTURING',
    Company= 'Journeyhorizon',
    Country= 'United Kingdom',
    LeadRole__c= 'Coach',
    ProductOfInterest__c= 'BASIC_ACCOUNT_PLUS',
    SubscriptionStatus__c= 'non-subscriber',
    Website= 'https://www.journeyh.io',
    Email= 'tabdeen.dxb@gmail.com',
    LeadSource= 'Webform',
    Status= 'MQL');
leads.add(l);

insert leads;