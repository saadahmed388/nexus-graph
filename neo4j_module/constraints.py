CONSTRAINTS = [

"""
CREATE CONSTRAINT ticket_issue_key IF NOT EXISTS
FOR (t:ticket)
REQUIRE t.issue_key IS UNIQUE
""",

"""
CREATE CONSTRAINT person_id IF NOT EXISTS
FOR (p:person)
REQUIRE p.id IS UNIQUE
""",

"""
CREATE CONSTRAINT track_name IF NOT EXISTS
FOR (t:track)
REQUIRE t.name IS UNIQUE
""",

"""
CREATE CONSTRAINT system_name IF NOT EXISTS
FOR (s:system)
REQUIRE s.name IS UNIQUE
""",

"""
CREATE CONSTRAINT environment_name IF NOT EXISTS
FOR (e:environment)
REQUIRE e.name IS UNIQUE
""",

"""
CREATE CONSTRAINT label_name IF NOT EXISTS
FOR (l:label)
REQUIRE l.name IS UNIQUE
""",

"""
CREATE CONSTRAINT issue_type_name IF NOT EXISTS
FOR (i:issueType)
REQUIRE i.name IS UNIQUE
"""
]

def create_constraints(driver):

    with driver.session() as session:
        for query in CONSTRAINTS:
            session.run(query)

    print("All constraints created.")