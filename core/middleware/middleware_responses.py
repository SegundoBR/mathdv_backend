from rest_framework.response import Response


class SuccessResponse200:
    @staticmethod
    def success_response(response: Response):
        """Wrap or augment an existing DRF Response's data with a standard envelope

        This modifies the Response in-place to preserve Response type and headers
        so tests and other middleware that expect a DRF Response still work.
        """
        data = getattr(response, "data", None)

        if isinstance(data, dict):
            formatted_data = {
                "success": True,
                "status": response.status_code,
                **data,
            }
        elif isinstance(data, str):
            formatted_data = {
                "success": True,
                "status": response.status_code,
                "message": data,
            }
        elif isinstance(data, list):
            formatted_data = {
                "success": True,
                "status": response.status_code,
                "data": data,
            }
        else:
            formatted_data = {
                "success": True,
                "status": response.status_code,
                "message": "Operación exitosa.",
            }

        # Preserve headers and other Response properties by assigning .data
        response.data = formatted_data
        response.status_code = response.status_code
        return response
