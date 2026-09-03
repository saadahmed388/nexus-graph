GRAPH_DB_SCHEMA_JSON="""
{
  BELONGS_TO_TRACK: {
    type: "relationship",
    count: 5464,
    properties: {}
  },
  HAS_COMMENT: {
    type: "relationship",
    count: 21405,
    properties: {}
  },
  REPORTS: {
    type: "relationship",
    count: 5807,
    properties: {}
  },
  AFFECTS_SYSTEM: {
    type: "relationship",
    count: 5241,
    properties: {}
  },
  DUPLICATES: {
    type: "relationship",
    count: 2,
    properties: {}
  },
  track: {
    count: 17,
    relationships: {
      BELONGS_TO_TRACK: {
        count: 1107,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      name: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      }
    },
    labels: []
  },
  IMPACTS: {
    type: "relationship",
    count: 4705,
    properties: {}
  },
  CLONES: {
    type: "relationship",
    count: 359,
    properties: {}
  },
  IS_OF_TYPE: {
    type: "relationship",
    count: 5807,
    properties: {}
  },
  DEFECTS: {
    type: "relationship",
    count: 528,
    properties: {}
  },
  ticket: {
    count: 5807,
    relationships: {
      DEFECTS: {
        count: 106,
        properties: {},
        direction: "out",
        labels: ["ticket"]
      },
      HAS_INVESTIGATION: {
        count: 442,
        properties: {},
        direction: "out",
        labels: ["investigationReport"]
      },
      BELONGS_TO_TRACK: {
        count: 1107,
        properties: {},
        direction: "out",
        labels: ["track"]
      },
      CONTAINS_WBS_GANTT: {
        count: 3,
        properties: {},
        direction: "out",
        labels: ["ticket"]
      },
      HAS_REPOSITORY_OBJECTS: {
        count: 84,
        properties: {},
        direction: "out",
        labels: ["repositoryObjects"]
      },
      HAS_COMMENT: {
        count: 4041,
        properties: {},
        direction: "out",
        labels: ["comment"]
      },
      HAS_LABEL: {
        count: 1047,
        properties: {},
        direction: "out",
        labels: ["label"]
      },
      WATCHES: {
        count: 13922,
        properties: {},
        direction: "in",
        labels: ["person"]
      },
      REPORTS: {
        count: 5807,
        properties: {},
        direction: "in",
        labels: ["person"]
      },
      AFFECTS_SYSTEM: {
        count: 1065,
        properties: {},
        direction: "out",
        labels: ["system"]
      },
      DUPLICATES: {
        count: 2,
        properties: {},
        direction: "out",
        labels: ["ticket"]
      },
      IMPACTS: {
        count: 887,
        properties: {},
        direction: "out",
        labels: ["environment"]
      },
      CLONES: {
        count: 67,
        properties: {},
        direction: "out",
        labels: ["ticket"]
      },
      IS_OF_TYPE: {
        count: 1161,
        properties: {},
        direction: "out",
        labels: ["issueType"]
      }
    },
    type: "node",
    properties: {
      updated_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      description_original: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      sub_category: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      bug_type: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      rca_category: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      sprint: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      vector_embedding: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      },
      first_response_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      epic_name: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      resolution: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      due_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      summary_en: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      bug_category: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      epic_status: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      closed_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      department: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      issue_raised_fdp: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      severity: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      ended_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      issue_id: {
        existence: FALSE,
        type: "INTEGER",
        indexed: TRUE,
        unique: FALSE
      },
      status_category_changed_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      parent_key: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      description_en: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      business_area: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      resolved_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      priority: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      full_vector_embedding: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      },
      issue_key: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      },
      status_category: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      created_on: {
        existence: FALSE,
        type: "DATE_TIME",
        indexed: TRUE,
        unique: FALSE
      },
      summary_original: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      time_in_status: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      status: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      }
    },
    labels: []
  },
  investigationReport: {
    count: 2243,
    relationships: {
      HAS_INVESTIGATION: {
        count: 442,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      issue_key: {
        existence: FALSE,
        type: "STRING",
        indexed: FALSE,
        unique: FALSE
      },
      technical_entities: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      },
      vector_embedding: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      },
      important_findings: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      },
      resolution: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      investigation_summary: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      root_cause: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      }
    },
    labels: []
  },
  DISCOVERY_CONNECTED: {
    type: "relationship",
    count: 1,
    properties: {}
  },
  HAS_INVESTIGATION: {
    type: "relationship",
    count: 2066,
    properties: {}
  },
  repositoryObjects: {
    count: 468,
    relationships: {
      HAS_REPOSITORY_OBJECTS: {
        count: 84,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      owner: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      issue_key: {
        existence: FALSE,
        type: "STRING",
        indexed: FALSE,
        unique: FALSE
      },
      object_type: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      objects: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      vector_embedding: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      },
      repo_changes: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      track: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      }
    },
    labels: []
  },
  label: {
    count: 44,
    relationships: {
      HAS_LABEL: {
        count: 1047,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      name: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      }
    },
    labels: []
  },
  CONTAINS_WBS_GANTT: {
    type: "relationship",
    count: 7,
    properties: {}
  },
  issueType: {
    count: 8,
    relationships: {
      IS_OF_TYPE: {
        count: 1161,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      name: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      }
    },
    labels: []
  },
  environment: {
    count: 9,
    relationships: {
      IMPACTS: {
        count: 887,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      name: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      }
    },
    labels: []
  },
  HAS_REPOSITORY_OBJECTS: {
    type: "relationship",
    count: 463,
    properties: {}
  },
  system: {
    count: 14,
    relationships: {
      AFFECTS_SYSTEM: {
        count: 1065,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      name: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      }
    },
    labels: []
  },
  WATCHES: {
    type: "relationship",
    count: 13922,
    properties: {}
  },
  HAS_LABEL: {
    type: "relationship",
    count: 5221,
    properties: {}
  },
  BLOCKS: {
    type: "relationship",
    count: 2,
    properties: {}
  },
  person: {
    count: 98,
    relationships: {
      WATCHES: {
        count: 13922,
        properties: {},
        direction: "out",
        labels: ["ticket"]
      },
      REPORTS: {
        count: 5807,
        properties: {},
        direction: "out",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      name: {
        existence: FALSE,
        type: "STRING",
        indexed: FALSE,
        unique: FALSE
      },
      id: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: TRUE
      }
    },
    labels: []
  },
  comment: {
    count: 21405,
    relationships: {
      HAS_COMMENT: {
        count: 4041,
        properties: {},
        direction: "in",
        labels: ["ticket"]
      }
    },
    type: "node",
    properties: {
      issue_key: {
        existence: FALSE,
        type: "STRING",
        indexed: FALSE,
        unique: FALSE
      },
      comment_english: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      author: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      timestamp: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      comment_original: {
        existence: FALSE,
        type: "STRING",
        indexed: TRUE,
        unique: FALSE
      },
      vector_embedding: {
        existence: FALSE,
        type: "LIST",
        indexed: TRUE,
        unique: FALSE
      }
    },
    labels: []
  }
}
"""