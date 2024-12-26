# API Documentation

This document provides detailed information about the Back.Serv REST API endpoints.

## Base URL

All API URLs are relative to: `http://your-server:4093/`

## Authentication

Currently, the API uses a simple user_id system. Future versions may implement more robust authentication.

## Endpoints

### Submit Task

Submit a new task for processing.

```http
POST /submit_task
Content-Type: application/json

{
    "task_type": string,
    "task_params": object,
    "user_id": string
}
```

#### Parameters

- `task_type` (required): Type of task to execute
  - Possible values: "image_creation", "image_upscale", "face_swap", "video_creation"
- `task_params` (required): Parameters specific to the task type
- `user_id` (required): Identifier for the user submitting the task

#### Response

```json
{
    "ticket_id": "string",
    "serv_name": "string",
    "status": "Queueing"
}
```

#### Example

```bash
curl -X POST http://localhost:4093/submit_task \
     -H "Content-Type: application/json" \
     -d '{
           "task_type": "image_creation",
           "task_params": {
             "prompt": "a beautiful sunset"
           },
           "user_id": "user123"
         }'
```

### Query Task Status

Get the current status of a task.

```http
GET /query_task/<ticket_id>
```

#### Parameters

- `ticket_id` (required): The ID of the task to query

#### Response

```json
{
    "status": "string",
    "result_info": "string",
    "error_info": "string",
    "started_at": "datetime",
    "completed_at": "datetime"
}
```

#### Example

```bash
curl http://localhost:4093/query_task/abc123
```

### Cancel Task

Cancel a running or queued task.

```http
POST /cancel_task/<ticket_id>
```

#### Parameters

- `ticket_id` (required): The ID of the task to cancel

#### Response

```json
{
    "status": "Cancelled",
    "message": "Task successfully cancelled"
}
```

#### Example

```bash
curl -X POST http://localhost:4093/cancel_task/abc123
```

## Task Types and Parameters

### Image Creation

```json
{
    "task_type": "image_creation",
    "task_params": {
        "prompt": "string",
        "negative_prompt": "string",
        "width": integer,
        "height": integer
    }
}
```

### Image Upscale

```json
{
    "task_type": "image_upscale",
    "task_params": {
        "image_url": "string",
        "scale_factor": integer
    }
}
```

### Face Swap

```json
{
    "task_type": "face_swap",
    "task_params": {
        "source_image": "string",
        "target_image": "string"
    }
}
```

### Video Creation

```json
{
    "task_type": "video_creation",
    "task_params": {
        "prompt": "string",
        "duration": integer,
        "fps": integer
    }
}
```

## Error Handling

The API uses standard HTTP response codes:

- 200: Success
- 202: Accepted (for task submission)
- 400: Bad Request
- 404: Not Found
- 500: Internal Server Error

Error responses include a message explaining the error:

```json
{
    "error": "string",
    "message": "string"
}
```
